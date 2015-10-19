from django.conf.urls import patterns, include, url

# Uncomment the next two lines to enable the admin:
from django.contrib import admin
admin.autodiscover()

urlpatterns = patterns('',
    # Index
    url(r'^$', 'sideloader.views.index', name='home'),

    # Projects
    url(r'^projects/create$', 'sideloader.views.projects_create', name='projects_create'),
    url(r'^projects/edit/(?P<id>[\w-]+)$', 'sideloader.views.projects_edit', name='projects_edit'),
    url(r'^projects/view/(?P<id>[\w-]+)$', 'sideloader.views.projects_view', name='projects_view'),
    url(r'^projects/build/(?P<id>[\w-]+)$', 'sideloader.views.projects_build', name='projects_build'),
    url(r'^projects/delete/(?P<id>[\w-]+)$', 'sideloader.views.projects_delete', name='projects_delete'),

    url(r'^projects/build/view/(?P<id>[\w-]+)$', 'sideloader.views.build_view', name='build_view'),
    url(r'^projects/build/log/(?P<id>[\w-]+)$', 'sideloader.views.build_output', name='build_output'),
    url(r'^projects/build/cancel/(?P<id>[\w-]+)$', 'sideloader.views.build_cancel', name='build_cancel'),

    # Repos
    url(r'^repo/create/(?P<project>[\w-]+)$', 'sideloader.views.repo_create', name='repo_create'),
    url(r'^repo/edit/(?P<id>[\w-]+)$', 'sideloader.views.repo_edit', name='repo_edit'),
    url(r'^repo/delete/(?P<id>[\w-]+)$', 'sideloader.views.repo_delete', name='repo_delete'),


    # Streams
    url(r'^stream/edit/(?P<id>[\w-]+)$', 'sideloader.views.stream_edit', name='stream_edit'),
    url(r'^stream/delete/(?P<id>[\w-]+)$', 'sideloader.views.stream_delete', name='stream_delete'),
    url(r'^stream/suck/(?P<id>[\w-]+)$', 'sideloader.views.release_delete', name='release_delete'),
    url(r'^stream/create/(?P<project>[\w-]+)$', 'sideloader.views.stream_create', name='stream_create'),
    url(r'^stream/push/(?P<flow>[\w-]+)/(?P<build>[\w-]+)$', 'sideloader.views.stream_push', name='stream_push'),
    url(r'^stream/schedule/(?P<flow>[\w-]+)/(?P<build>[\w-]+)$', 'sideloader.views.stream_schedule', name='stream_schedule'),

    url(r'^stream/manifests/(?P<id>[\w-]+)$', 'sideloader.views.manifest_view', name='manifest_view'),
    url(r'^stream/manifests/add/(?P<id>[\w-]+)$', 'sideloader.views.manifest_add', name='manifest_add'),
    url(r'^stream/manifests/edit/(?P<id>[\w-]+)$', 'sideloader.views.manifest_edit', name='manifest_edit'),
    url(r'^stream/manifests/delete/(?P<id>[\w-]+)$', 'sideloader.views.manifest_delete', name='manifest_delete'),

    # Modules
    url(r'^modules/edit/(?P<id>[\w]+)$', 'sideloader.views.module_edit', name='module_edit'),
    url(r'^modules/create$', 'sideloader.views.module_create', name='module_create'),
    url(r'^modules/get_scheme/(?P<id>[\w]+)$', 'sideloader.views.module_scheme', name='module_scheme'),
    url(r'^modules/$', 'sideloader.views.module_index', name='module_index'),

    # Releases
    url(r'^releases/edit/(?P<id>[\w-]+)$', 'sideloader.views.release_edit', name='edit_release'),
    url(r'^releases/create$', 'sideloader.views.release_create', name='create_release'),
    url(r'^releases/$', 'sideloader.views.release_index', name='release_index'),

    # Servers
    url(r'^servers/$', 'sideloader.views.server_index', name='server_index'),
    url(r'^servers/log/(?P<id>[\w-]+)$', 'sideloader.views.server_log', name='server_log'),
    url(r'^servers/json/$', 'sideloader.views.get_servers', name='get_servers'),
    url(r'^servers/json/stream/(?P<id>[\w-]+)$', 'sideloader.views.get_stream_servers', name='get_stream_servers'),

    # Help
    url(r'^help/$', 'sideloader.views.help_index', name='help_index'),

    # Admin
    url(r'^manage/$', 'sideloader.views.manage_index', name='manage_index'),
    url(r'^manage/repo/create$', 'sideloader.views.manage_create_repo', name='manage_create_repo'),
    url(r'^manage/repo/delete/(?P<id>[\d+])$', 'sideloader.views.manage_delete_repo', name='manage_delete_repo'),

    # API
    url(r'^api/build/(?P<hash>[\w-]+)$', 'sideloader.views.api_build', name='api_build'),
    url(r'^api/rap/(?P<hash>[\w-]+)$', 'sideloader.views.api_sign', name='api_sign'),
    url(r'^api/checkin$', 'sideloader.views.api_checkin', name='api_checkin'),
    url(r'^api/enc/(?P<server>[\w.-]+)$', 'sideloader.views.api_enc', name='api_enc'),

    # Authentication
    url(r'^accounts/login/$', 'django.contrib.auth.views.login', {'template_name': 'login.html'}),
    url(r'^accounts/logout/$', 'django.contrib.auth.views.logout', {'next_page': '/'}, name='auth_logout'),
    url(r'^accounts/profile/$', 'sideloader.views.accounts_profile', name='accounts_profile'),

    # Uncomment the next line to enable the admin:
    url(r'^admin/', include(admin.site.urls)),
)
