# touchstone_python
Unofficial API Wrapper for [Touchstone](touchstone.email) and [Touchstone Tests](touchstonetests.io).
Created by watching requests go in and out of the website.

### Installation

`pip install git+https://git@github.com/wjziv/touchstone_python.git@master#egg=touchstone`


### Touchstone Dashboarding

Coming Soon!

### Touchstone Tests

The primary usage of this module at the time of deployment is to provide a method for automated data uploads to Touchstone Tests as a means of keeping the Subject Line data up-to-date.

##### Example Usage

```python
from touchstone import TouchstoneTests

username = 'user'
password = 'pass'

with TouchstoneTests(username, password) as ts:
    ts.upload_data('filename.txt')
```
