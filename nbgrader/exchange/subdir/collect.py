import os
import glob
import shutil
import sys
from collections import defaultdict
from textwrap import dedent
import datetime

from nbgrader.exchange.abc import ExchangeCollect as ABCExchangeCollect
from nbgrader.exchange.default import ExchangeCollect as DefaultExchangeCollect
from .exchange import Exchange

from nbgrader.utils import check_mode, parse_utc
from ...api import Gradebook, MissingEntry
from ...utils import check_mode, parse_utc

# pwd is for matching unix names with student ide, so we shouldn't import it on
# windows machines
if sys.platform != 'win32':
    import pwd
else:
    pwd = None


def groupby(l, key=lambda x: x):
    d = defaultdict(list)
    for item in l:
        d[key(item)].append(item)
    return d


class ExchangeCollect(Exchange, DefaultExchangeCollect):
    def init_src(self):
        if self.coursedir.course_id == '':
            self.fail("No course id specified. Re-run with --course flag.")

        if self.no_course_id:
            self.course_path = os.path.join(self.root)
        else:
            self.course_path = os.path.join(self.root, self.coursedir.course_id)

        self.inbound_path = os.path.join(self.course_path, 'inbound')
        if not os.path.isdir(self.inbound_path):
            self.fail("Course not found: {}".format(self.inbound_path))
        if not check_mode(self.inbound_path, read=True, execute=True):
            self.fail("You don't have read permissions for the directory: {}".format(self.inbound_path))
        student_id = self.coursedir.student_id if self.coursedir.student_id else '*'
        if self.subdirs:
            pattern = os.path.join(self.inbound_path, student_id, '{}+{}+*'.format(student_id, self.coursedir.assignment_id))
        else:
            pattern = os.path.join(self.inbound_path, '{}+{}+*'.format(student_id, self.coursedir.assignment_id))

        records = [self._path_to_record(f) for f in glob.glob(pattern)]
        usergroups = groupby(records, lambda item: item['username'])

        with Gradebook(self.coursedir.db_url, self.coursedir.course_id) as gb:
            try:
                assignment = gb.find_assignment(self.coursedir.assignment_id)
                self.duedate = assignment.duedate
            except MissingEntry:
                self.duedate = None
        if self.duedate is None or not self.before_duedate:
            self.src_records = [self._sort_by_timestamp(v)[0] for v in usergroups.values()]
        else:
            self.src_records = []
            for v in usergroups.values():
                records = self._sort_by_timestamp(v)
                records_before_duedate = [record for record in records if record['timestamp'] <= self.duedate]
                if records_before_duedate:
                    self.src_records.append(records_before_duedate[0])
                else:
                    self.src_records.append(records[0])



    def copy_files(self):
        if len(self.src_records) == 0:
            self.log.warning("No submissions of '{}' for course '{}' to collect".format(
                self.coursedir.assignment_id,
                self.coursedir.course_id))
        else:
            self.log.info("Processing {} submissions of '{}' for course '{}'".format(
                len(self.src_records),
                self.coursedir.assignment_id,
                self.coursedir.course_id))

        for rec in self.src_records:
            student_id = rec['username']
            if self.subdirs:
                src_path = os.path.join(self.inbound_path, student_id, rec['filename'])
            else:
                src_path = os.path.join(self.inbound_path, rec['filename'])

            # Cross check the student id with the owner of the submitted directory
            if self.check_owner and pwd is not None: # check disabled under windows
                try:
                    owner = pwd.getpwuid(os.stat(src_path).st_uid).pw_name
                except KeyError:
                    owner = "unknown id"
                if student_id != owner:
                    self.log.warning(dedent(
                        """
                        {} claims to be submitted by {} but is owned by {}; cheating attempt?
                        you may disable this warning by unsetting the option CollectApp.check_owner
                        """).format(src_path, student_id, owner))

            dest_path = self.coursedir.format_path(self.coursedir.submitted_directory, student_id, self.coursedir.assignment_id)
            if not os.path.exists(os.path.dirname(dest_path)):
                os.makedirs(os.path.dirname(dest_path))

            copy = False
            updating = False
            if os.path.isdir(dest_path):
                existing_timestamp = self.coursedir.get_existing_timestamp(dest_path)
                new_timestamp = rec['timestamp']
                if self.update and (existing_timestamp is None or new_timestamp > existing_timestamp):
                    copy = True
                    updating = True
                elif self.before_duedate and existing_timestamp != new_timestamp:
                    copy = True
                    updating = True

            else:
                copy = True

            if copy:
                if updating:
                    self.log.info("Updating submission: {} {}".format(student_id, self.coursedir.assignment_id))
                    shutil.rmtree(dest_path)
                else:
                    self.log.info("Collecting submission: {} {}".format(student_id, self.coursedir.assignment_id))
                self.do_copy(src_path, dest_path)
            else:
                if self.update:
                    self.log.info("No newer submission to collect: {} {}".format(
                        student_id, self.coursedir.assignment_id
                    ))
                else:
                    self.log.info("Submission already exists, use --update to update: {} {}".format(
                        student_id, self.coursedir.assignment_id
                    ))
