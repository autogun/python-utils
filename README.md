# python-utils
Personal python utils to make my daily work easier

- pr_comment.py
  - I use this to post a comment on the current working PR to execute CI build
  
- OpenProxyDetector.py
  - This was built in mind to run on AWS Lambda with an access to DynamoDB & SES servcies for a list of proxy hosts and email service.
    Checks if proxy host is an open proxy both via browser and non-browser user-agent.
    Sends an email when such host is detected

- updateSecurityGroupEC2.py
  - When I find myself on the road and my 4G egress IP constantly changing, this little piece helps me update pre-configured security groups with the current IP instead of previously used, based on rule description.

- multihome.sh
  - If you ever require to have one interface accepting incoming connections while the other interface to be used as outbound interface only. Wrote this with docker support in mind.
