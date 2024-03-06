# Django Energysystem Viewer

This app holds functionality to examine energysystem network, aggregations and search abbreviations.

## Installation

Install app via pip (currently only as GitHub dependency):

```bash
pip install git+https://github.com/sedos-project/django_energysystem_viewer.git
```

Add app to your installed apps in django project settings:

```python
DJANGO_APPS = [
    ...,
    "django_energysystem_viewer",
]
```

and add related urls in project urls.py like:

```python
urlpatterns = [
    ...,
    path("", include("django_energysystem_viewer.urls")),
]
```

## For developers

### Versioning

You can automatically bump current version by using `bump-my-version` tool.
You can run `bump-my-version show-bump` to see resulting versions.
