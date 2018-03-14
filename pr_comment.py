#!/usr/bin/env python2

import httplib
import json
import os
import subprocess
import sys
import urllib2


ORG_NAME = ''
REPO_NAME = ''
COMMENT_TEXT = ''
GITHUB_API_HOST = 'api.github.com'
API_BASE_URL = 'https://{}/repos/{}/{}'.format(GITHUB_API_HOST, ORG_NAME, REPO_NAME)
GITHUB_API_TOKEN = '<token>' or os.getenv('GITHUB_API_TOKEN')


def get_current_branch_pr():
    try:
        current_branch = subprocess.check_output(['/usr/bin/git', 'rev-parse', '--abbrev-ref', 'HEAD'],
                                                 stderr=subprocess.STDOUT)
    except subprocess.CalledProcessError as err:
        print 'ERROR: Could not get current branch name: {}'.format(err.output)
        sys.exit(1)

    url = '{}/pulls?head={}:{}'.format(API_BASE_URL, ORG_NAME, current_branch)
    req = urllib2.Request(url)
    req.add_header('Authorization', 'token {}'.format(GITHUB_API_TOKEN))
    resp = urllib2.urlopen(req)

    content = json.loads(resp.read())
    if len(content) < 1:
        print 'ERROR: Could not find correlating pull request for branch {}'.format(current_branch)
        sys.exit(1)

    pr = content[0]['number']
    return pr


def post_comment_to_pr(pr_number):
    request_path = '/repos/{}/{}/issues/{}/comments'.format(ORG_NAME, REPO_NAME, pr_number)
    body = json.dumps({
        'body': COMMENT_TEXT
    })
    headers = {
        'User-Agent': 'python-comment',
        'Content-Type': 'application/json',
        'Authorization': 'token {}'.format(GITHUB_API_TOKEN)
    }

    conn = httplib.HTTPSConnection(GITHUB_API_HOST)
    conn.set_debuglevel(1)
    conn.request('POST', request_path, body, headers)
    response = conn.getresponse()
    print response.status, response.reason
    data = response.read()
    print data

    conn.close()


def main():
    pr_number = get_current_branch_pr()
    post_comment_to_pr(pr_number)


if __name__ == '__main__':
    if not GITHUB_API_TOKEN:
        print 'ERROR: GitHub API token missing. Please pass `GITHUB_API_TOKEN`'
        sys.exit(1)

    main()
