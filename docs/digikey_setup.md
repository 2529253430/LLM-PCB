# DigiKey Provider Setup

## 1. Create a DigiKey developer application

Create an application in the DigiKey API Developer Portal and obtain:

- Client ID
- Client Secret

Use Product Information V4 access.

Do not commit credentials to Git.

## 2. Configure PowerShell environment variables

For the current PowerShell window:

```powershell
$env:DIGIKEY_CLIENT_ID="your-client-id"
$env:DIGIKEY_CLIENT_SECRET="your-client-secret"
$env:DIGIKEY_SITE="SG"
$env:DIGIKEY_LANGUAGE="en"
$env:DIGIKEY_CURRENCY="SGD"
$env:DIGIKEY_SHIP_TO_COUNTRY="SG"
```

These values disappear after the PowerShell window is closed.

To store them for the current Windows user:

```powershell
[Environment]::SetEnvironmentVariable(
    "DIGIKEY_CLIENT_ID",
    "your-client-id",
    "User"
)

[Environment]::SetEnvironmentVariable(
    "DIGIKEY_CLIENT_SECRET",
    "your-client-secret",
    "User"
)
```

Open a new terminal after setting persistent variables.

## 3. Run offline tests

The tests use a fake transport and do not access DigiKey:

```powershell
python -m pytest test/test_digikey_provider.py -v
```

## 4. Run a real search

From the project root:

```powershell
python -m examples.search_digikey_components
```

## Security

Never place the Client Secret in:

- source code;
- README screenshots;
- Git commits;
- JSON configuration committed to the repository.

The local raw response cache is stored in:

```text
data/cache/digikey/
```

Add this directory to `.gitignore`.
