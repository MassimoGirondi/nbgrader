import base64
import os
import secrets
from stat import (
    S_IRUSR, S_IWUSR, S_IXUSR,
    S_IRGRP, S_IWGRP, S_IXGRP,
    S_IROTH, S_IWOTH, S_IXOTH
)
from textwrap import dedent

from nbgrader.exchange.abc import ExchangeSubmit as ABCExchangeSubmit
from nbgrader.exchange.default import ExchangeSubmit as DefaultExchangeSubmit
from traitlets import Bool

from .exchange import Exchange
from nbgrader.utils import get_username, check_mode, find_all_notebooks


class ExchangeSubmit(Exchange, DefaultExchangeSubmit):
    def init_dest(self):
        if self.coursedir.course_id == '':
            self.fail("No course id specified. Re-run with --course flag.")
        if not self.authenticator.has_access(self.coursedir.student_id, self.coursedir.course_id):
            self.fail("You do not have access to this course.")

        if self.no_course_id:
            self.inbound_path = os.path.join(self.root, 'inbound')
            self.cache_path = os.path.join(self.cache)
        else:
            self.inbound_path = os.path.join(self.root, self.coursedir.course_id, 'inbound')
            self.cache_path = os.path.join(self.cache, self.coursedir.course_id)

        if self.subdirs:
            self.inbound_path= os.path.join(self.inbound_path, get_username())

        if not os.path.isdir(self.inbound_path):
            self.fail("Inbound directory doesn't exist: {}".format(self.inbound_path))
        if not check_mode(self.inbound_path, write=True, execute=True):
            self.fail("You don't have write permissions to the directory: {}".format(self.inbound_path))


        if self.coursedir.student_id != '*':
            # An explicit student id has been specified on the command line; we use it as student_id
            if '*' in self.coursedir.student_id or '+' in self.coursedir.student_id:
                self.fail("The student ID should contain no '*' nor '+'; got {}".format(self.coursedir.student_id))
            student_id = self.coursedir.student_id
        else:
            student_id = get_username()
        if self.add_random_string:
            random_str = base64.urlsafe_b64encode(os.urandom(9)).decode('ascii')
            self.assignment_filename = '{}+{}+{}+{}'.format(
                student_id, self.coursedir.assignment_id, self.timestamp, random_str)
        else:
            self.assignment_filename = '{}+{}+{}'.format(
                student_id, self.coursedir.assignment_id, self.timestamp)

    def init_release(self):
        if self.coursedir.course_id == '':
            self.fail("No course id specified. Re-run with --course flag.")

        if self.no_course_id:
            course_path = os.path.join(self.root)
        else:
            course_path = os.path.join(self.root, self.coursedir.course_id)

        outbound_path = os.path.join(course_path, 'outbound')
        self.release_path = os.path.join(outbound_path, self.coursedir.assignment_id)
        if not os.path.isdir(self.release_path):
            self.fail("Assignment not found: {}".format(self.release_path))
        if not check_mode(self.release_path, read=True, execute=True):
            self.fail("You don't have read permissions for the directory: {}".format(self.release_path))

    def copy_files(self):
        self.init_release()
        submission_secret = secrets.token_hex(64)

        dest_path = os.path.join(self.inbound_path, self.assignment_filename)

        if self.add_random_string:
            cache_path = os.path.join(self.cache_path, self.assignment_filename.rsplit('+', 1)[0])
        else:
            cache_path = os.path.join(self.cache_path, self.assignment_filename)

        self.log.info("Source: {}".format(self.src_path))
        self.log.info("Destination: {}".format(dest_path))

        # copy to the real location
        self.check_filename_diff()
        self.do_copy(self.src_path, dest_path)
        with open(os.path.join(dest_path, "timestamp.txt"), "w") as fh:
            fh.write(self.timestamp)
        with open(os.path.join(dest_path, "submission_secret.txt"), "w") as fh:
            fh.write(submission_secret)
        self.set_perms(
            dest_path,
            fileperms=(S_IRUSR | S_IWUSR | S_IRGRP | S_IROTH),
            dirperms=(S_IRUSR | S_IWUSR | S_IXUSR | S_IRGRP | S_IXGRP | S_IROTH | S_IXOTH))

        # Make this 0777=ugo=rwx so the instructor can delete later. Hidden from other users by the timestamp.
        os.chmod(
            dest_path,
            S_IRUSR|S_IWUSR|S_IXUSR|S_IRGRP|S_IWGRP|S_IXGRP|S_IROTH|S_IWOTH|S_IXOTH
        )

        # also copy to the cache
        if not os.path.isdir(self.cache_path):
            os.makedirs(self.cache_path)
        self.do_copy(self.src_path, cache_path)
        with open(os.path.join(cache_path, "timestamp.txt"), "w") as fh:
            fh.write(self.timestamp)
        with open(os.path.join(cache_path, "submission_secret.txt"), "w") as fh:
            fh.write(submission_secret)

        self.log.info("Submitted as: {} {} {}".format(
            self.coursedir.course_id, self.coursedir.assignment_id, str(self.timestamp)
        ))
