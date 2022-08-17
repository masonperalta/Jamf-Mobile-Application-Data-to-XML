# Gather Mobile Application Data to XML


## Purpose
The purpose of this script is to sync mobile device applications via the Jamf Classic API and append various data elements to a primary XML file that can be uploaded to a BI tool.

### Datapoints Collected for Mobile Devices Applications:
```xml
<mobile_device_applications>
  <mobile_device_application>
    <application_name>My App</application_name>
    <bundle_id>com.my-app</bundle_id>
    <application_status>Managed</application_status>
    <devices>
      <device>
        <id>1</id>
        <app_version>1.0</app_version>
      </device>
    </devices>
  </mobile_device_application>
</mobile_device_applications>
```
