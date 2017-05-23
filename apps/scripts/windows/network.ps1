# autor: Filip Varga

function Disable-DynamicDNSRegistraion(){
    [CmdletBinding()]
    param([Alias("ComputerName")] [string[]] $hostnames = "localhost",
          [Alias("Credential")] [pscredential] [System.Management.Automation.Credential()] $cred = [pscredential]::empty)

    $jobs = New-Object System.Collections.ArrayList

    foreach ($hostname in $hostnames) {
        $job = Invoke-Command -AsJob -ComputerName $hostname -Credential $cred -ScriptBlock {
            foreach ($interface in (get-wmiobject "win32_ip4routetable where destination='0.0.0.0'")) {
                foreach ($conf in (get-wmiobject -class win32_networkadapterconfiguration)) {
                    if ($conf.interfaceindex -ne $interface.interfaceindex) {
                        $conf.setdynamicdnsregistration($false) | Out-Null
                    }
                }
            }
        }
        $jobs.Add($job) | Out-Null
    }

    while ($true){
        for ($i = 0; $i -lt $jobs.Count; $i++) {
            $job = $jobs[$i]
            if (($job.State -eq "Failed") -or ($job.State -eq "Completed")) {
                # TODO: asynchronne vracat novy objekt
                Write-Host "$($job.Location): $($job.State)"
                $jobs.RemoveAt($i--)
                Remove-Job $job
            }
        }
        if (-not $jobs) {break}
        Start-Sleep -Seconds 1
    }
}
# Disable-DynamicDNSRegistraion -ComputerName ((Get-ADComputer -Filter * -SearchBase "OU=Computers,OU=GKUBA,OU=GKU,DC=SKGEODESY,DC=LOCAL").DNSHostName | where { $_ -ne $null })