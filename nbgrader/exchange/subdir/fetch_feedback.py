import os
import shutil
import glob

from nbgrader.exchange.abc import ExchangeFetchFeedback as ABCExchangeFetchFeedback
from nbgrader.exchange.default import ExchangeFetchFeedback as DefaultExchangeFetchFeedback
from .exchange import Exchange

from nbgrader.utils import check_mode, notebook_hash, make_unique_key, get_username


class ExchangeFetchFeedback(Exchange, DefaultExchangeFetchFeedback):
    def init_src(self):
        if self.coursedir.course_id == '':
            self.fail("No course id specified. Re-run with --course flag.")

        if self.no_course_id:
            self.course_path = os.path.join(self.root)
            self.cache_path = os.path.join(self.cache)
        else:
            self.course_path = os.path.join(self.root, self.coursedir.course_id)
            self.cache_path = os.path.join(self.cache, self.coursedir.course_id)

        if self.subdirs:
            self.outbound_path = os.path.join(self.course_path, 'outbound-feedback', get_username())
        else:
            self.outbound_path = os.path.join(self.course_path, 'outbound-feedback')
        self.src_path = os.path.join(self.outbound_path)

        if self.coursedir.student_id != '*':
            # An explicit student id has been specified on the command line; we use it as student_id
            if '*' in self.coursedir.student_id or '+' in self.coursedir.student_id:
                self.fail("The student ID should contain no '*' nor '+'; got {}".format(self.coursedir.student_id))
            student_id = self.coursedir.student_id
        else:
            student_id = get_username()

        if not os.path.isdir(self.src_path):
            self._assignment_not_found(
                self.src_path,
                os.path.join(self.outbound_path, "*"))
        if not check_mode(self.src_path, execute=True):
            self.fail("You don't have execute permissions for the directory: {}".format(self.src_path))

        assignment_id = self.coursedir.assignment_id if self.coursedir.assignment_id else '*'
        pattern = os.path.join(self.cache_path, '*+{}+*'.format(assignment_id))
        self.log.debug(
            "Looking for submissions with pattern: {}".format(pattern))

        self.feedback_files = []
        submissions = [os.path.split(x)[-1] for x in glob.glob(pattern)]
        for submission in submissions:
            _, assignment_id, timestamp = submission.split('/')[-1].split('+')

            self.log.debug(
                "Looking for feedback for '{}/{}' submitted at {}".format(
                    self.coursedir.course_id, assignment_id, timestamp))
            pattern = os.path.join(self.cache_path, submission, "*.ipynb")
            notebooks = glob.glob(pattern)

            # Check if a secret is provided
            submission_secret = None
            submission_secret_path = os.path.join(self.cache_path, submission, "submission_secret.txt")
            if os.path.isfile(submission_secret_path):
                with open(submission_secret_path) as fh:
                    submission_secret = fh.read()

            for notebook in notebooks:
                notebook_id = os.path.splitext(os.path.split(notebook)[-1])[0]

                # If a secret is provided, use that
                # If not, fall back to using make_unique_key
                if submission_secret:
                    nb_hash = notebook_hash(secret=submission_secret, notebook_id=notebook_id)
                    feedbackpath = os.path.join(self.outbound_path, '{0}.html'.format(nb_hash))
                    if os.path.exists(feedbackpath):
                        self.feedback_files.append((notebook_id, timestamp, feedbackpath))
                        self.log.info(
                            "Found feedback for '{}/{}/{}' submitted at {}".format(
                                self.coursedir.course_id, assignment_id, notebook_id, timestamp))
                        continue

                else:

                    unique_key = make_unique_key(
                        self.coursedir.course_id,
                        assignment_id,
                        notebook_id,
                        student_id,
                        timestamp)

                    # Try legacy hashing 1
                    nb_hash = notebook_hash(notebook, unique_key)
                    feedbackpath = os.path.join(self.outbound_path, '{0}.html'.format(nb_hash))
                    if os.path.exists(feedbackpath):
                        self.feedback_files.append((notebook_id, timestamp, feedbackpath))
                        self.log.info(
                            "Found feedback for '{}/{}/{}' submitted at {}".format(
                                self.coursedir.course_id, assignment_id, notebook_id, timestamp))
                        continue

                    # If it doesn't exist, try legacy hashing 2
                    nb_hash = notebook_hash(notebook)
                    feedbackpath = os.path.join(self.outbound_path, '{0}.html'.format(nb_hash))
                    if os.path.exists(feedbackpath):
                        self.feedback_files.append((notebook_id, timestamp, feedbackpath))
                        self.log.warning(
                            "Found legacy feedback for '{}/{}/{}' submitted at {}".format(
                                self.coursedir.course_id, assignment_id, notebook_id, timestamp))
                        continue

                # If we reached here, then there's no feedback available
                self.log.warning(
                    "Could not find feedback for '{}/{}/{}' submitted at {}".format(
                        self.coursedir.course_id, assignment_id, notebook_id, timestamp))

    def init_dest(self):
        if self.path_includes_course:
            root = os.path.join(self.coursedir.course_id, self.coursedir.assignment_id)
        else:
            root = self.coursedir.assignment_id
        self.dest_path = os.path.abspath(os.path.join(self.assignment_dir, root, 'feedback'))

