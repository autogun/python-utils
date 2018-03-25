# python-utils
Personal python utils to make my daily work easier

- pr_comment.py
  - I use this to post a comment on the current working PR to execute CI build
  
- OpenProxyDetector.py
  - This was built in mind to run on AWS Lambda with an access to DynamoDB & SES servcies for a list of proxy hosts and email service.
    Checks if proxy host is an open proxy both via browser and non-browser user-agent.
