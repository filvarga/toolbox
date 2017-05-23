# autor: Filip Varga

# TODO: skontroluj ci moze scheduled job
# vymazat sam seba pocas behu
function Update-Windows() {
    [CmdletBinding()]
    param([Alias("ComputerName")] [string[]] $hostnames = "localhost",
          [Alias("Credential")] [pscredential] [System.Management.Automation.Credential()] $cred = [pscredential]::empty,
          [Alias("MicrosoftUpdate")] [switch] $online,
          [Alias("RestartComputer")] [switch] $reboot)
    
    if ($online) {
        $service_name = "Microsoft Update"
    } else {
        $service_name = "Windows Server Update Service"
    }

    $jobs = New-Object System.Collections.ArrayList

    foreach ($hostname in $hostnames){
        $job = Invoke-Command -AsJob -ComputerName $hostname -Credential $cred -ArgumentList $service_name, $reboot -ScriptBlock {
            Register-ScheduledJob -Name "Windows-Update-Script" -RunNow -ArgumentList $args[0], $args[1] -ScriptBlock {
                $result = $null
                $logfile = "C:\Windows-Update-Script.txt"
                $session = New-Object -ComObject "Microsoft.Update.Session"

                $installer = $session.CreateUpdateInstaller()

                "$(Get-Date) Windows-Update-Script started" | Out-File -Append $logfile
                # TODO: zabal do funkcie
                if ($installer.RebootRequiredBeforeInstallation) {
                    "$(Get-Date) Reboot Required Before Installation" | Out-File -Append $logfile
                    Unregister-ScheduledJob "Windows-Update-Script" -ErrorAction SilentlyContinue
                    "$(Get-Date) Windows-Update-Script finished" | Out-File -Append $logfile
                    if ($args[1]) {Restart-Computer}
                    else {return}
                }

                foreach ($svc in (New-Object -ComObject "Microsoft.Update.ServiceManager").Services) {
                    if ($svc.Name -eq $args[0]) {
                        $searcher = $session.CreateUpdateSearcher()

                        if ($args[0] == "Microsoft Update") {
                            $searcher.ServerSelection = 2
                        } elseif ($args[0] = "Windows Server Update Service") {
                            $searcher.ServerSelection = 3 
                            $searcher.ServiceID = $svc.ServiceID
                        }
                                        
                        try {$result = $searcher.Search($searcher.EscapeString("isInstalled=0 and isHidden=0"))}
                        catch {
                            "$(Get-Date) Update Searcher error '$($_.Exception.Message)'" | Out-File -Append $logfile
                            Unregister-ScheduledJob "Windows-Update-Script" -ErrorAction SilentlyContinue
                            "$(Get-Date) Windows-Update-Script finished" | Out-File -Append $logfile
                            return
                        } # error
                        break
                    }
                }
                if ($result -eq $null) {
                    "$(Get-Date) Update Searcher result empty" | Out-File -Append $logfile
                    Unregister-ScheduledJob "Windows-Update-Script" -ErrorAction SilentlyContinue
                    "$(Get-Date) Windows-Update-Script finished" | Out-File -Append $logfile
                    return
                } # error

                $updates = New-Object -ComObject "Microsoft.Update.UpdateColl"
                $downloader = $session.CreateUpdateDownloader()

                # download one by one update
                foreach ($update in $result.Updates) {
                    $update.AcceptEula()

                    $coll = New-Object -ComObject "Microsoft.Update.UpdateColl"
                    $coll.Add($update) | Out-Null
                    $downloader.Updates = $coll

                    try {$result = $downloader.Download()}
                    catch {
                        "$(Get-Date) Update Downlader error '$($_.Exception.Message)'" | Out-File -Append $logfile
                        Unregister-ScheduledJob "Windows-Update-Script" -ErrorAction SilentlyContinue
                        continue
                    } # error
                    if ($result.ResultCode -eq 2) {
                        # Update downloaded !!!
                        $updates.Add($update) | Out-Null
                        # debug:
                        "$(Get-Date) Update downloaded" | Out-File -Append $logfile
                    }
                }

                # install one by one update
                foreach ($update in $updates) {
                    $coll = New-Object -ComObject "Microsoft.Update.UpdateColl"
                    $coll.Add($update) | Out-Null
                    $installer.Updates = $coll

                    try {$result = $installer.Install()}
                    catch {
                        "$(Get-Date) Update Installer error '$($_.Exception.Message)'" | Out-File -Append $logfile
                        Unregister-ScheduledJob "Windows-Update-Script" -ErrorAction SilentlyContinue
                        continue
                        } # error
                    if ($result.ResultCode -eq 2) {
                        # Update installed !!!
                        # debug:
                        "$(Get-Date) Update installed" | Out-File -Append $logfile
                    }
                }
                Unregister-ScheduledJob "Windows-Update-Script" -ErrorAction SilentlyContinue
                
                # TODO: skontrolovat ci funguje
                if ($installer.RebootRequiredBeforeInstallation) {
                    "$(Get-Date) Reboot Required Before Installation" | Out-File -Append $logfile
                    "$(Get-Date) Windows-Update-Script finished" | Out-File -Append $logfile
                    if ($args[1]) {Restart-Computer}
                } else {
                    "$(Get-Date) Windows-Update-Script finished" | Out-File -Append $logfile
                }
            }
        }
        $jobs.Add($job) | Out-Null
    }

    # TODO: premysli logiku - najdi ine sposoby

    while ($true) {
        for ($i = 0; $i -lt $jobs.Count; $i++) {
            $job = $jobs[$i]
            if (($job.State -eq "Failed") -or ($job.State -eq "Completed")) {
                Write-Host "$($job.Location): $($job.State)"
                $jobs.RemoveAt($i--)
                Remove-Job $job
            }
        }
        if (-not $jobs) {break}
        Start-Sleep -Seconds 5
    }
}
# $computer = "gkuba013"
# Update-Windows -ComputerName $computer -MicrosoftUpdate -RestartComputer
# Update-Windows -ComputerName (Get-ADComputer -Filter * -SearchBase "CN=Computers, DC=CONTOSO, DC=COM").Name -MicrosoftUpdate -RestartComputer
# Update-Windows -ComputerName ((Get-ADComputer -Filter * -SearchBase "CN=Computers,DC=CONTOSO,DC=COM").DNSHostName | where { $_ -ne $null }) -MicrosoftUpdate -RestartComputer
# Invoke-Command -ComputerName $computer -ScriptBlock {Get-ScheduledJob}
# Invoke-Command -ComputerName $computer -ScriptBlock {Get-Content -Path "C:\Windows-Update-Script.txt"}
# Get-Content -Path "C:\Windows-Update-Script.txt" -Tail 1 –Wait