# Script to automate starting Amphetype windows.
# This activates the environment, then start the application as a background process

Write-Host "[amphetype launcher] Activating Python Environment"
.\.venv\Scripts\activate
Write-Host "[amphetype launcher] Start Amphetype as a background process"
python .\bootstrap.py &
Write-Host "[amphetype launcher] Deactivate Python Environment"
deactivate
