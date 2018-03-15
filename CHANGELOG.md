Release Notes
=============

Version 1.2.0
-------------

Released 2018-03-15

* Fix context manager so transactions are rolled back on commit errors
  (fixes #25)
* Change default behaviour of context manager so sessions are closed
  on worker teardown rather than context manager exit (closes #24)
  
Version 1.1.0
-------------

Released 2018-02-24

* Added `transaction_retry` decorator to reattempt transactions
  after temporary loss of connectivity to the database
* Added missing cleanup that left connections open on kill (fixes #12)

Version 1.0.0
-------------

Released 2017-12-07

* Added a new dependency with on demand worker scoped session
  and with a session context manager

Version 0.1.0
-------------

Released 2017-02-20

* Added `db_engine_options` fixture.
* Switched to semantic versioning.

Version 0.0.4
-------------

Released 2016-09-02

* Fix packaging so pytest fixtures added in 0.0.3 are included.

Version 0.0.3
-------------

Released 2016-08-26

* Added `pytest` fixtures for managing session in tests.
 
Version 0.0.2
-------------

Released 2016-05-11

* Create engine once at setup, and dispose of it again on stop.

Version 0.0.1
-------------

Released 2015-04-01

* Initial release.
