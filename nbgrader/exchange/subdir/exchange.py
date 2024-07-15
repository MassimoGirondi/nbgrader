import os
import datetime
import sys
import shutil
import glob

from textwrap import dedent


from rapidfuzz import fuzz
from traitlets import Unicode, Bool, default
from jupyter_core.paths import jupyter_data_dir

from nbgrader.exchange.abc import Exchange as ABCExchange
from nbgrader.exchange.default import Exchange as DefaultExchange
from nbgrader.exchange import ExchangeError
from nbgrader.utils import check_directory, ignore_patterns, self_owned


class Exchange(DefaultExchange):
    subdirs = Bool(
                True,
                help="Whether the assignments would live in users' subfolder (e.g. course/assigments/user/assignment1/..."
                ).tag(config=True)
    no_course_id = Bool(
                True,
                help=dedent("""Whether the assignments would live in course's subfolder (e.g. {course}/assigments/user/assignment1/...)
                    or directly in the exchange folder""")
                ).tag(config=True)

    def start(self):
        if sys.platform == 'win32':
            self.fail("Sorry, the exchange is not available on Windows.")
        if not self.coursedir.groupshared:
            # This just makes sure that directory is o+rwx.  In group shared
            # case, it is up to admins to ensure that instructors can write
            # there.
            self.ensure_root()

        return super(Exchange, self).start()
