# testext_python
Unofficial API Wrapper for [TestText](testtext.com).
Created by watching requests go in and out of the website.

### Installation

`pip install git+https://git@github.com/wjziv/testtext_python.git@master#egg=testtext`


### TestText

The primary usage of this module at the time of deployment is to provide a method for automated data uploads to TestText as a means of keeping the Subject Line and SMS data up-to-date.

TestText only accepts valid TSV file formats at the moment.

##### Example Usage

```python
from testtext import TestText

username = 'user'
password = 'pass'

with TestTest(username, password) as tt:
    tt.upload_data('filename.tsv')
```
