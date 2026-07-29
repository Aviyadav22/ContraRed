# ContraRed Word Add-in Installation Guide

This guide explains the two ways ContraRed can be installed in Microsoft Word. Use Part 1 when the organization has Microsoft 365 admin support. Use Part 2 when an individual user needs to install the add-in manually.

## Quick Recommendation

For most small teams:

1. Use the ContraRed dashboard first. It works directly in the browser.
2. Install the Word add-in manually only on the devices where contract review will happen in Word.
3. If more team members need the Word add-in, repeat the manual installation on each device.

## Part 1: Microsoft 365 / IT Team Deployment

Use this route when the organization has Microsoft 365 admin access or an IT/admin person.

### Best for

- Larger teams.
- Organizations with Microsoft 365 Business or Enterprise administration.
- Central deployment to multiple users.
- A cleaner long-term rollout without asking each user to install manually.

### Steps

1. Open Microsoft 365 Admin Center.
2. Go to Settings > Integrated apps.
3. Choose Upload custom apps.
4. Upload the ContraRed `manifest.xml` file or provide the hosted manifest URL.
5. Assign access to selected users or a security group.
6. Ask users to restart Microsoft Word.
7. Users open Word and launch ContraRed from the ribbon/add-ins area.

### Network Access Required

Allow outbound HTTPS access to:

- `https://contrared-addin.netlify.app`
- `https://contrared-api.onrender.com`
- `https://appsforoffice.microsoft.com`
- `https://fonts.googleapis.com`
- `https://fonts.gstatic.com`

### Notes

- This does not require ContraRed to be listed on Microsoft AppSource.
- This is the preferred rollout path for larger or more formal deployments.
- The add-in is privately hosted and can be deployed using the provided manifest.
- The hosted manifest and add-in assets have been deployed and validated.

## Part 2: Manual Deployment For Individual Users

Use this route when there is no IT team or no Microsoft 365 admin deployment.

### Best for

- Individual users.
- Small teams testing on a few laptops.
- Users who can install the add-in themselves.

### What To Use

ContraRed can be used in two ways:

1. Browser dashboard: easiest and works immediately.
2. Microsoft Word add-in: best experience for reviewing and applying redlines inside Word.

### Option A: Word On The Web

Use this if Word Online shows an upload option.

1. Open Word on the web.
2. Open any document.
3. Go to Insert > Add-ins.
4. Choose Upload My Add-in.
5. Upload `manifest.xml`.
6. Open ContraRed from the add-ins/ribbon area.

If the Upload My Add-in option is not visible, use the Windows desktop option.

### Option B: Word Desktop On Windows

Use the ContraRed Word add-in ZIP package.

1. Download and extract `ContraRed-Word-Addin.zip`.
2. Right-click `Install-ContraRed.bat`.
3. Choose Run as administrator.
4. Restart Microsoft Word completely.
5. Open any Word document.
6. Go to Insert > Get Add-ins or My Add-ins.
7. Open the Shared Folder tab.
8. Select ContraRed and click Add.

### What The Installer Does

The installer creates a local trusted Office add-in catalog on the device:

`\\localhost\ContraRed-Addin`

It then places the ContraRed manifest in that folder so Word can load the add-in.

### Important Notes

- This is a manual per-device installation.
- It is not a Microsoft AppSource installation.
- It does not automatically roll out to the whole organization.
- If Windows asks for administrator permission, approve it only if the ZIP came directly from ContraRed.
- If Word or the Microsoft account blocks custom add-ins, use the dashboard instead.
- The add-in UI loads from ContraRed's hosted site, so most product updates can happen without reinstalling the add-in.
- If the manifest itself changes later, the local install package may need to be reinstalled.

## Data Handling Reminder

Before scanning documents, users should confirm that the document type is permitted under their organization's data-handling, confidentiality, and external processing requirements.

## Support

If installation is blocked, the fastest fallback is to use the ContraRed dashboard link in the browser.
