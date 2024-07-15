import os
import shutil
from stat import (
    S_IRUSR, S_IWUSR, S_IXUSR,
    S_IRGRP, S_IWGRP, S_IXGRP,
    S_IROTH, S_IWOTH, S_IXOTH,
    S_ISGID, ST_MODE
)


from nbgrader.exchange.abc import ExchangeReleaseAssignment as ABCExchangeReleaseAssignment
from nbgrader.exchange.default import ExchangeReleaseAssignment as DefaultExchangeReleaseAssignment
from .exchange import Exchange


class ExchangeReleaseAssignment(Exchange, DefaultExchangeReleaseAssignment):
    def init_dest(self):
        if self.coursedir.course_id == '':
            self.fail("No course id specified. Re-run with --course flag.")

        if self.no_course_id:
            self.course_path = os.path.join(self.root)
        else:
            self.course_path = os.path.join(self.root, self.coursedir.course_id)

        self.outbound_path = os.path.join(self.course_path, 'outbound')
        self.inbound_path = os.path.join(self.course_path, 'inbound')
        self.dest_path = os.path.join(self.outbound_path, self.coursedir.assignment_id)
        # 0755
        # groupshared: +2040
        self.ensure_directory(
            self.course_path,
            S_IRUSR|S_IWUSR|S_IXUSR|S_IRGRP|S_IXGRP|S_IROTH|S_IXOTH|((S_ISGID|S_IWGRP) if self.coursedir.groupshared else 0)
        )
        # 0755
        # groupshared: +2040
        self.ensure_directory(
            self.outbound_path,
            S_IRUSR|S_IWUSR|S_IXUSR|S_IRGRP|S_IXGRP|S_IROTH|S_IXOTH|((S_ISGID|S_IWGRP) if self.coursedir.groupshared else 0)
        )
        # 0733 with set GID so student submission will have the instructors group
        # groupshared: +0040
        self.ensure_directory(
            self.inbound_path,
            S_ISGID|S_IRUSR|S_IWUSR|S_IXUSR|S_IWGRP|S_IXGRP|S_IWOTH|S_IXOTH|(S_IRGRP if self.coursedir.groupshared else 0)
        )
    
