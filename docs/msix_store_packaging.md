# Microsoft Store MSIX packaging

This project keeps PyInstaller as the build layer and adds MSIX as a packaging layer on top of the existing Windows `dist` output.

## Why MSIX for Store distribution

- Microsoft Store distribution with MSIX is the preferred signing route for this app: the Store signs the package during submission.
- A separate commercial code-signing certificate is not required for Store MSIX publishing.
- Local sideload testing still needs either a trusted test certificate or loose-package registration.

## Prerequisites

- Windows 10/11.
- Python dependencies installed for the project.
- Windows 10/11 SDK with `MakeAppx.exe` if you want the script to create the `.msix` file.
- A reserved app identity in Partner Center for the final Store submission.

## Build an MSIX package

From the repository root:

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File scripts\package_msix_win.ps1
```

The script:

1. runs `scripts\build_win.bat` unless `-SkipBuild` is passed;
2. stages `dist\MindNavigator (windows 11 x64)` into `dist\msix\staging`;
3. writes `dist\msix\staging\AppxManifest.xml` from `packaging\msix\AppxManifest.xml.in`;
4. generates MSIX logo PNG files from `assets\icon.ico`;
5. creates `dist\msix\MindNavigator.msix` with `MakeAppx.exe`.

For Partner Center identity values, pass the package metadata explicitly:

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File scripts\package_msix_win.ps1 `
  -PackageName "PartnerCenter.PackageName" `
  -Publisher "CN=PublisherFromPartnerCenter" `
  -PublisherDisplayName "Publisher Display Name" `
  -Version "1.0.0.0"
```

Use `-StageOnly` to create only the loose package directory for local registration/debugging:

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File scripts\package_msix_win.ps1 -StageOnly
```

Then register the loose package:

```powershell
Add-AppxPackage -Register dist\msix\staging\AppxManifest.xml
```

## Store submission notes

- Replace placeholder manifest identity values with the values assigned by Partner Center.
- `MakeAppx.exe` creates `.msix` or `.msixbundle`; Microsoft documents `.msixupload` as the recommended Store upload artifact. Use Visual Studio packaging or the MSIX Packaging Tool if Partner Center requires an upload package for the final submission.
- Do not store production certificates, PFX files, or Partner Center credentials in this repository.

## Non-Store distribution

If the same package is distributed outside the Microsoft Store, it must be signed separately with a trusted signing method before users can install it.
