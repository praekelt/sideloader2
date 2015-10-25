import time
from django.db import models
from django.conf import settings
from django.utils import timezone


class Project(models.Model):
    name = models.CharField(max_length=255, unique=True)
    allowed_users = models.ManyToManyField(settings.AUTH_USER_MODEL, blank=True)

    def __unicode__(self):
        return self.name

    def __str__(self):
        return self.__unicode__().encode('utf-8', 'replace')

class Repo(models.Model):
    github_url = models.CharField(max_length=255)

    project = models.ForeignKey(Project)

    default_branch = models.CharField(max_length=255, default='develop')

    build_type = models.CharField(max_length=64, default='virtualenv')
    deploy_file = models.CharField(
        max_length=255, default='.deploy.yaml', blank=True)

    package_name = models.CharField(max_length=255, default='', blank=True)

    build_script = models.CharField(max_length=255, default='', blank=True)

    postinstall_script = models.CharField(
        max_length=255, default='', blank=True)

    # Built-in version retriever
    version_getter = models.CharField(max_length=64, default='setup.py')

    # Command to retrieve version
    version_cmd = models.TextField(blank=True)

    build_counter = models.IntegerField(default=0)

    created_by_user = models.ForeignKey(settings.AUTH_USER_MODEL, related_name="ProjectCreatedBy")
    idhash = models.CharField(max_length=48)

    notifications = models.BooleanField(default=True)
    slack_channel = models.CharField(max_length=255, default='', blank=True)

    def __unicode__(self):
        return self.github_url

    def __str__(self):
        return self.__unicode__().encode('utf-8', 'replace')

class Server(models.Model):
    name = models.CharField(max_length=255)
    last_checkin = models.DateTimeField(auto_now_add=True)
    last_puppet_run = models.DateTimeField(auto_now_add=True)
    status = models.CharField(max_length=255, default='', blank=True)
    change = models.BooleanField(default=True)
    specter_status = models.CharField(max_length=255, default='', blank=True)

    ip_address = models.CharField(max_length=255, default='', blank=True)

    memory = models.IntegerField()
    cores = models.IntegerField()
    
    disks = models.CharField(max_length=255, default='', blank=True)

    project = models.ForeignKey(Project, blank=True)

    def age(self):
        """Returns seconds since last checkin"""
        now = timezone.now()
        return int((now - self.last_checkin).total_seconds())

    def __unicode__(self):
        return self.name

    def __str__(self):
        return self.__unicode__().encode('utf-8', 'replace')

class ServerRequest(models.Model):
    name = models.CharField(max_length=255)

    requested_by = models.ForeignKey(settings.AUTH_USER_MODEL, related_name="ServerRequestedBy")

    inftype = models.CharField(max_length=255)

    cpus = models.IntegerField(default=2)
    memory = models.IntegerField(default=2)
    disk = models.IntegerField(default=50)

    project = models.ForeignKey(Project, blank=True)

    approved_by = models.ForeignKey(settings.AUTH_USER_MODEL, related_name="ServerApprovedBy", blank=True, null=True)

    approval = models.IntegerField(default=0)

    provisioned = models.BooleanField(default=False)

    request_date = models.DateTimeField(auto_now_add=True)

    def __unicode__(self):
        return self.name

    def __str__(self):
        return self.__unicode__().encode('utf-8', 'replace')

class PackageRepo(models.Model):
    name = models.CharField(max_length=255)
    cmd = models.TextField()

    project = models.ForeignKey(Project, blank=True, null=True)

    created_by_user = models.ForeignKey(settings.AUTH_USER_MODEL, related_name="PackageRepoCreatedBy")

    def __unicode__(self):
        return self.name

    def __str__(self):
        return self.__unicode__().encode('utf-8', 'replace')

class Build(models.Model):
    repo = models.ForeignKey(Repo)

    branch = models.CharField(max_length=256)

    build_num = models.IntegerField()

    build_time = models.DateTimeField(auto_now_add=True)

    # 0 - queued, 1 - In progress, 2 - Success, 3 - Failed, 4 - Canceled
    state = models.IntegerField(default=0)

    task_id = models.CharField(max_length=255, default='')

    log = models.TextField(default="")

    version = models.CharField(max_length=255)

    build_file = models.CharField(max_length=255)


class Target(models.Model):
    description = models.CharField(max_length=256)

    stream_mode = models.CharField(max_length=64, default='repo')

    custom_script = models.TextField(blank=True)

    package_repo = models.ForeignKey(PackageRepo, blank=True, null=True)

    server = models.ForeignKey(Server, blank=True, null=True)

    post_deploy = models.TextField(blank=True)

    current_build = models.ForeignKey(Build, null=True, blank=True)

    log = models.TextField(default="")

    project = models.ForeignKey(Project)

    # 0 - Nothing, 1 - In progress, 2 - Good, 3 - Bad
    state = models.IntegerField(default=0)

    def __unicode__(self):
        return self.description

    def __str__(self):
        return self.__unicode__().encode('utf-8', 'replace')

class Stream(models.Model):
    name = models.CharField(max_length=255)
    repo = models.ForeignKey(Repo)

    package_type = models.CharField(max_length=64, default='deb') #DEB, RPM, TAR, Docker..

    post_build = models.TextField(blank=True)

    branch = models.CharField(max_length=256, default='develop')
    architecture = models.CharField(max_length=64, default='amd64')

    require_signoff = models.BooleanField(default=False)
    signoff_list = models.TextField(blank=True)
    quorum = models.IntegerField(default=0)

    auto_release = models.BooleanField(default=False)

    notify = models.BooleanField(default=False)
    notify_list = models.TextField(blank=True)

    project = models.ForeignKey(Project)

    targets = models.ManyToManyField(Target, blank=True)

    def __unicode__(self):
        return self.name

    def __str__(self):
        return self.__unicode__().encode('utf-8', 'replace')

    def email_list(self):
        if not '@' in self.signoff_list:
            return []

        return self.signoff_list.replace('\r', ' ').replace(
            '\n', ' ').replace(',', ' ').strip().split()


class Release(models.Model):
    release_date = models.DateTimeField(auto_now_add=True)

    stream = models.ForeignKey(Stream)

    build = models.ForeignKey(Build)

    scheduled = models.DateTimeField(blank=True, null=True)
    
    waiting = models.BooleanField(default=True)

    lock = models.BooleanField(default=False)

    def signoff_count(self):
        return self.releasesignoff_set.filter(signed=True).count()

    def signoff_remaining(self):
        q = self.flow.quorum
        if q == 0:
            return len(self.flow.email_list()) - self.signoff_count()
        return self.flow.quorum - self.signoff_count()

    def check_signoff(self):
        if not self.flow.require_signoff:
            return True

        if self.signoff_remaining()>0:
            return False

        return True

    def check_schedule(self):
        if not self.scheduled:
            return True

        t = int(time.mktime(self.scheduled.timetuple()))
        if (time.time() - t) > 0:
            return True
        return False

    def release_state(self):
        if self.waiting:
            if self.flow.require_signoff:
                # Sign-offs required
                remaining = self.signoff_remaining()
                if (remaining > 0):
                    return (3, remaining)

            if self.check_schedule():
                return (4, None)
            return (2, self.scheduled)
        else:
            return (1, None)

    def get_state(self):
        c, s = self.release_state()

        messages = {
            1: lambda t: "Deployed",
            2: lambda t: "Scheduled for %s (UTC)" % t.strftime("%d-%m-%Y @ %H:%M"),
            3: lambda t: "Waiting for %s signature%s" % (t, t>1 and 's' or ''),
            4: lambda t: "Running..."
        }
        
        return messages[c](s)

    def __repr__(self):
        return "<Release(release_date=%s, flow=%s, build=%s, scheduled=%s, waiting=%s, lock=%s)>" % (
            self.release_date, self.flow.id, self.build.id, self.scheduled,
            self.waiting, self.lock
        )

class ReleaseSignoff(models.Model):
    release = models.ForeignKey(Release)
    signature = models.CharField(max_length=255)
    idhash = models.CharField(max_length=48)
    signed = models.BooleanField(default=False)

