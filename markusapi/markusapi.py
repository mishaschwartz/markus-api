# Interface for python to interact with MarkUs API.
#
# The purpose of this Python module is for users to be able to 
# perform MarkUs API functions without having to 
# specify the API auth key and URL with each call.
#
##  DISCLAIMER
#
# This script is made available under the OSI-approved
# MIT license. See http://www.markusproject.org/#license for
# more information. WARNING: This script is still considered
# experimental.
#
# (c) by the authors, 2008 - 2019.
#

import http.client
import json
import mimetypes
import sys
from typing import Optional, List, Union
from urllib.parse import urlparse, urlencode


class Markus:
    """A class for interfacing with the MarkUs API."""

    API_PATH = '/api'  # The root api path.

    def __init__(self, api_key: str, url: str) -> 'Markus':
        """
        Initialize an instance of the Markus class.

        A valid API key can be found on the dashboard page of the GUI,
        when logged in as an admin.

        Keywork arguments:
        api_key  -- any admin API key for the MarkUs instance.
        url      -- the root domain of the MarkUs instance.
        """
        self.api_key = api_key
        self.parsed_url = urlparse(url.strip())
        assert self.parsed_url.scheme in ['http', 'https']

    def get_all_users(self) -> List[dict]:
        """
        Return a list of every user in the MarkUs instance.
        Each user is a dictionary object, with the following keys:
        'id', 'user_name', 'first_name', 'last_name',
        'type', 'grace_credits', 'notes_count'.
        """
        params = None
        response = self.submit_request(params, '/api/users.json', 'GET')
        return Markus.decode_json_response(response)

    def new_user(self, user_name: str, user_type: str, first_name: str,
                 last_name: str, section_name: Optional[str] = None, 
                 grace_credits: Optional[str] = None) -> List[str]:
        """
        Add a new user to the MarkUs database.
        Returns a list containing the response's status,
        reason, and data.
        """
        params = { 
            'user_name': user_name,
            'type': user_type,
            'first_name': first_name,
            'last_name': last_name
            }
        if section_name != None:
            params['section_name'] = section_name
        if grace_credits != None:
            params['grace_credits'] = grace_credits
        return self.submit_request(params, '/api/users', 'POST')

    def get_assignments(self) -> List[dict]:
        """
        Return a list of all assignments.
        """
        params = None
        response = self.submit_request(params, '/api/assignments.json', 'GET')
        return Markus.decode_json_response(response)

    def get_groups(self, assignment_id: int) -> List[dict]:
        """
        Return a list of all groups associated with the given assignment.
        """
        params = None
        path = Markus.get_path(assignments=assignment_id) + '.json'
        response = self.submit_request(params, path, 'GET')
        return Markus.decode_json_response(response)

    def get_groups_by_name(self, assignment_id: int) -> dict:
        """
        Return a dictionary mapping group names to group ids.
        """
        params = None
        path = Markus.get_path(assignments=assignment_id, group_ids_by_name=None) + '.json'
        response = self.submit_request(params, path, 'GET')
        return Markus.decode_json_response(response)

    def get_group(self, assignment_id: int, group_id: int) -> dict:
        """
        Return the group info associated with the given id and assignment.
        """
        params = None
        path = Markus.get_path(assignments=assignment_id, groups=group_id) + '.json'
        response = self.submit_request(params, path, 'GET')
        return Markus.decode_json_response(response)

    def get_feedback_files(self, assignment_id: int, group_id: int) -> List[dict]:
        """
        Get the feedback files info associated with the assignment and group.
        """
        params = {}
        path = Markus.get_path(assignments=assignment_id, groups=group_id, feedback_files=None) + '.json'
        response = self.submit_request(params, path, 'GET')
        return Markus.decode_json_response(response)

    def get_feedback_file(self, assignment_id: int, group_id: int, feedback_file_id: int) -> str:
        """
        Get the feedback file associated with the given id, assignment and group.
        WARNING: This will fail for non-text feedback files
        """
        params = {}
        path = Markus.get_path(assignments=assignment_id, groups=group_id, feedback_files=feedback_file_id) + '.json'
        response = self.submit_request(params, path, 'GET')
        return Markus.decode_text_response(response)

    def get_marks_spreadsheet(self, spreadsheet_id: int) -> str:
        """
        Get the marks spreadsheet associated with the given id.
        """
        params = {}
        path = Markus.get_path(grade_entry_forms=spreadsheet_id) + '.json'
        response = self.submit_request(params, path, 'GET')
        return Markus.decode_text_response(response)

    def upload_feedback_file(self, assignment_id: int, group_id: int, title: str, 
                             contents: Union[str, bytes], mime_type: Optional[str] = None, overwrite: bool = True) -> List[str]:
        """
        Upload a feedback file to Markus.

        Keyword arguments:
        assignment_id -- the assignment's id
        group_id      -- the id of the group to which we are uploading
        title         -- the file name that will be displayed (a file extension is required)
        contents      -- what will be in the file (can be a string or bytes)
        mime_type     -- mime type of title file, if None then the mime type will be guessed based on the file extension 
        overwrite     -- whether to overwrite a feedback file with the same name that already exists in Markus
        """
        feedback_file_id = None
        if overwrite:
            feedback_files = self.get_feedback_files(assignment_id, group_id)
            feedback_file_id = next((ff.get('id') for ff in feedback_files if ff.get('filename') == title), None)
        path = Markus.get_path(assignments=assignment_id, groups=group_id, feedback_files=None)
        request_type = 'POST'
        if feedback_file_id:
            path = '{}/{}'.format(path, feedback_file_id)
            request_type = 'PUT'

        if mime_type is None:
            mime_type = mimetypes.guess_type(title)[0]
        
        if mime_type is None:
            raise ValueError(f'if the mime_type argument is not given you must provide a title file with a valid extension')

        if isinstance(contents, str):
            params = {
                'filename': title,
                'file_content': contents,
                'mime_type': mime_type
            }
            content_type = 'application/x-www-form-urlencoded'
        else:  # binary data
            params = {
                'filename': title.encode('utf-8'),
                'file_content': contents,
                'mime_type': mime_type.encode('utf-8')
            }
            content_type = 'multipart/form-data'
        return self.submit_request(params, path, request_type, content_type)

    def upload_test_group_results(self, assignment_id: int, group_id: int, test_run_id: int, test_output: str) -> List[str]:
        """ Upload test results to Markus """
        params = {
            'test_run_id': test_run_id,
            'test_output': test_output
        }
        path = Markus.get_path(assignments=assignment_id, groups=group_id, test_group_results=None)
        return self.submit_request(params, path, 'POST')

    def upload_annotations(self, assignment_id: int, group_id: int, annotations: dict, force_complete: bool = False) -> List[str]:
        """
        Each element of annotations must be a dictionary with the following keys:
            - filename
            - annotation_category_name
            - content
            - line_start
            - line_end
            - column_start
            - column_end

        This currently only works for plain-text file submissions.
        """
        params = {
            'annotations': annotations,
            'force_complete': force_complete
        }
        path = Markus.get_path(assignments=assignment_id, groups=group_id, add_annotations=None)
        return self.submit_request(params, path, 'POST', 'application/json')

    def update_marks_single_group(self, criteria_mark_map: dict, assignment_id: int, group_id: int) -> List[str]:
        """
        Update the marks of a single group. 
        Only the marks specified in criteria_mark_map will be changed.
        To set a mark to unmarked, use 'nil' as it's value.
        Otherwise, marks must have valid numeric types (floats or ints).
        Criteria are specified by their title. Titles must be formatted
        exactly as they appear in the MarkUs GUI, punctuation included.
        If the criterion is a Rubric, the mark just needs to be the
        rubric level, and will be multiplied by the weight automatically.

        Keyword arguments:
        criteria_mark_map -- maps criteria to the desired grade
        assignment_id     -- the assignment's id
        group_id          -- the id of the group whose marks we are updating
        """
        params = criteria_mark_map
        path = Markus.get_path(assignments=assignment_id, groups=group_id, update_marks=None)
        return self.submit_request(params, path, 'PUT')

    def update_marking_state(self, assignment_id: int, group_id: int, new_marking_state: str) -> List[str]:
        """ Update marking state for a single group to either 'complete' or 'incomplete' """
        params = {
            'marking_state': new_marking_state
        }
        path = Markus.get_path(assignments=assignment_id, groups=group_id, update_marking_state=None)
        return self.submit_request(params, path, 'PUT')

    def submit_request(self, params: Optional[dict], path: str, request_type: str, content_type: str = 'application/x-www-form-urlencoded') -> List[str]:
        """ Return result from _do_submit_request after formatting the params and setting headers """
        headers = {'Content-type': content_type}
        if params is not None:
            if content_type == 'application/x-www-form-urlencoded':
                # simple params, sent as form query string (needs url encoding of reserved and non-alphanumeric chars)
                params = urlencode(params)
            elif content_type == 'multipart/form-data':
                # complex params like binary files, sent as-is (assumes already-encoded data)
                pass
            elif content_type == 'application/json':
                # json-encoded params
                params = json.dumps(params)
            if not isinstance(params, str):
                raise ValueError('If the params are not a string type object please provide a valid content_type')
        if request_type == 'GET':  # we only want this for GET requests
            headers['Accept'] = 'text/plain'
        return self._do_submit_request(params, path, request_type, headers)

    def _do_submit_request(self, params: Optional[str], path: str, request_type: str, headers: dict) -> List[str]:
        """
        Perform the HTTP/HTTPS request. Return a list 
        containing the response's status, reason, and content.

        Keyword arguments:
        params       -- contains the parameters of the request
        path         -- route to the resource we are targetting
        request_type -- the desired HTTP method (usually 'GET' or 'POST')
        """
        auth_header = 'MarkUsAuth {}'.format(self.api_key)
        headers['Authorization'] = auth_header
        resp = None
        conn = None
        if self.parsed_url.scheme == 'http':
            conn = http.client.HTTPConnection(self.parsed_url.netloc)
        elif self.parsed_url.scheme == 'https':
            conn = http.client.HTTPSConnection(self.parsed_url.netloc)
        else:
            raise ValueError('Panic! Neither http nor https URL.')
        conn.request(request_type,
                     self.parsed_url.path + path,
                     params,
                     headers)
        resp = conn.getresponse()
        lst = [resp.status, resp.reason, resp.read()]
        conn.close()
        return lst


    # Helpers

    @staticmethod
    def get_path(**kwargs):
        path = '/'.join([str(v) for vals in kwargs.items() for v in vals if v is not None])
        return f'{Markus.API_PATH}/{path}'

    @staticmethod
    def decode_text_response(resp: bytes) -> str:
        """Converts response from submit_request into a utf-8 string."""
        return resp[2].decode('utf-8')

    @staticmethod
    def decode_json_response(resp: bytes) -> dict:
        """Converts response from submit_request into python dict."""
        return json.loads(Markus.decode_text_response(resp))
