import os
import shutil

from nbgrader.exchange.abc import ExchangeFetchAssignment as ABCExchangeFetchAssignment
from nbgrader.exchange.default import ExchangeFetchAssignment as DefaultExchangeFetchAssignment
from .exchange import Exchange
from nbgrader.utils import check_mode


class ExchangeFetchAssignment(Exchange, DefaultExchangeFetchAssignment):
    def init_src(self):
        if self.coursedir.course_id == '':
            self.fail("No course id specified. Re-run with --course flag.")
        if not self.authenticator.has_access(self.coursedir.student_id, self.coursedir.course_id):
            self.fail("You do not have access to this course.")

        if self.path_includes_course:
            self.course_path = os.path.join(self.root, self.coursedir.course_id)
        else:
            self.course_path = self.root

        self.outbound_path = os.path.join(self.course_path, 'outbound')
        self.src_path = os.path.join(self.outbound_path, self.coursedir.assignment_id)
        if not os.path.isdir(self.src_path):
            self._assignment_not_found(
                self.src_path,
                os.path.join(self.outbound_path, "*"))
        if not check_mode(self.src_path, read=True, execute=True):
            self.fail("You don't have read permissions for the directory: {}".format(self.src_path))

