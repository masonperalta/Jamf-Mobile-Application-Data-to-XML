# Jamf Mobile Application Data to XML


## Purpose
The purpose of this script is to sync mobile device applications via the Jamf Classic API and append various data elements to a primary XML file that can be uploaded to a BI tool.

### Datapoints Collected for Mobile Devices Applications:
```xml
<mobile_device_applications>
  <mobile_device_application>
    <application_id>1</application_id>
    <application_name>My App</application_name>
    <bundle_id>com.my-app</bundle_id>
    <devices>
      <device>
        <id>1</id>
        <application_version>1.0</app_version>
        <application_status>Managed</application_status>
      </device>
    </devices>
  </mobile_device_application>
</mobile_device_applications>
```

Configure the .ENV file as follows:
```
JSSUSER = "api_user"
JSSPASS = "api_user_pw"
JSS = "https://myInstance.jamfcloud.com"
SERVERTYPE = "windows"
```
