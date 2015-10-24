from django.contrib.auth.models import User
from django import forms
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Submit
import models


class BaseModelForm(forms.ModelForm):
    helper = FormHelper()
    helper.form_class = 'form-horizontal'
    helper.label_class = 'col-lg-2'
    helper.field_class = 'col-lg-8'
    helper.add_input(Submit('submit', 'Submit'))

class BaseForm(forms.Form):
    helper = FormHelper()
    helper.form_class = 'form-horizontal'
    helper.label_class = 'col-lg-2'
    helper.field_class = 'col-lg-8'
    helper.add_input(Submit('submit', 'Submit'))

class ProjectForm(BaseModelForm):
    allowed_users = forms.ModelMultipleChoiceField(
        queryset=User.objects.all().order_by('username'),
        required=False
    )

    allowed_users.help_text = ''

    class Meta:
        model = models.Project
        exclude = ()

class PackageRepoForm(BaseModelForm):
    class Meta:
        model = models.PackageRepo
        exclude = ()

class RepoForm(BaseModelForm):
    github_url = forms.CharField(label="Git checkout URL")

    build_type = forms.ChoiceField(
        label='Deploy type',
        widget=forms.Select,
        choices=(
            ('virtualenv', 'Virtualenv'),
            ('python', 'Python package'), ('flat', 'Flat')))

    version_getter = forms.ChoiceField(
        label='Package version',
        widget=forms.Select,
        choices=(
            ('setup.py', 'Python setup.py'),
            ('autonum', 'Auto increment'),
            ('script', 'Custom script'),
        )
    )
    version_cmd = forms.CharField(
        widget=forms.Textarea,
        label="Version script",
        required=False
    )

    class Meta:
        model = models.Repo
        exclude = ('idhash', 'created_by_user', 'build_counter', 'project')

    def clean(self):
        cleaned_data = super(RepoForm, self).clean()

        uri = cleaned_data['github_url'].strip()
        if not (uri[-4:] == '.git'):
            raise forms.ValidationError("Not a valid Git URI")

        cleaned_data['github_url'] = uri

        return cleaned_data

class TargetForm(BaseModelForm):


    class Meta:
        model = models.Target
        exclude = ('current_build', 'log', 'state', 'project')

class StreamForm(BaseModelForm):

    targets = forms.ModelMultipleChoiceField(
        queryset=models.Target.objects.all(),
        required=False
    )

    targets.help_text = ''

    package_type = forms.ChoiceField(
        label='Package type',
        widget=forms.Select,
        choices=(
            ('deb', 'Debian/Ubuntu'),
            ('rpm', 'RedHat'),
            ('docker', 'Docker image'),
            ('dockerhub', 'Docker Hub'),
            ('tar', 'TAR file'),
            ('pypi', 'PyPi Upload')
        )
    )

    architecture = forms.ChoiceField(
        label='CPU architecture',
        widget=forms.Select,
        choices=(
            ('amd64', 'amd64'),
            ('i386', 'i386'),
        )
    )

    auto_release = forms.BooleanField(
        help_text="Automatically deploy new builds to this release workflow",
        required=False)

    require_signoff = forms.BooleanField(
        label="Require sign-off",
        required=False)

    signoff_list = forms.CharField(
        widget=forms.Textarea,
        label="Sign-off list",
        required=False,
        help_text="List email addresses on a new line")

    quorum = forms.IntegerField(
        required=False,
        initial=0,
        help_text="Required number of sign-offs before release. 0 means <strong>all</strong> are required")
    
    notify = forms.BooleanField(
        label="Notify",
        help_text="Send notifications of releases by email",
        required=False)

    class Meta:
        model = models.Stream
        exclude = ('project',)
        fields = (
            'name', 'repo', 'branch', 'package_type', 'architecture',
            'targets',
            'post_build', 'auto_release', 'require_signoff',
            'signoff_list', 'notify', 'notify_list',
        )

#class ModuleForm(BaseModelForm):
#    class Meta:
#        model = models.ModuleManifest
#        fields = ('name', 'key', 'structure',)

#class ManifestForm(BaseModelForm):
#    class Meta:
#        model = models.ServerManifest
#        exclude = ('release',)

class UserForm(BaseModelForm):
    password = forms.CharField(widget=forms.PasswordInput(), initial='')
    class Meta:
        model = User
        exclude = (
            'email', 'username', 'is_staff', 'is_active', 'is_superuser',
            'last_login', 'date_joined', 'groups', 'user_permissions'
        )
