Changelog
=========

0.1.3 - (2021-06-09)
--------------------

- Cleaned up the email validation tests.

0.1.2 - (2020-12-03)
--------------------

- Forgot that ``title_or_id`` returns an encoded ``str``; reencode that
  back into ``unicode`` to prevent automatic wrongful ascii conversion.

0.1.1 - (2014-10-15)
--------------------

- Ignore cases where the event does not provide the required attributes.

0.1 - (2014-10-13)
------------------

- Initial release.
- Reports workflow changes via email as defined in the registry.
- Hooks into Workspace and Exposure objects defined in pmr2.app.
