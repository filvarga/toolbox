# autor: Filip Varga

function Get-NetworkAddress() {
    [CmdletBinding()]
    param([Alias("IPAddress")] [IPAddress] $address,
          [Alias("NetworkMask")] [IPAddress] $netmask)

    $broadcast = New-Object System.Collections.ArrayList

    $bAddress = $address.GetAddressBytes()
    $bNetmask = $netmask.GetAddressBytes()

    for ($i = 0; $i -le 3; $i++){
        $broadcast.Add($bAddress[$i] -band $bNetmask[$i]) | Out-Null
    }
    return [IPAddress]($broadcast -Join ".")
}

function Set-RouteLocal() {
    [CmdletBinding()]
    param([Alias("DefaultGateway")] [IPAddress] $gateway,
          [Alias("DestinationPrefix")] [string] $prefix,
          [Alias("RouteMetric")] [int] $metric)

    $route = Get-NetRoute "0.0.0.0/0" -ErrorAction SilentlyContinue | Where-Object NextHop -eq $gateway

    if ($route){
        Remove-NetRoute -DestinationPrefix $prefix -ErrorAction SilentlyContinue -Confirm:$false
        New-NetRoute -DestinationPrefix $prefix -InterfaceIndex $route.ifIndex -NextHop $gateway -RouteMetric $metric
    }
}

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

function Test-PSRemoting(){
    [CmdletBinding()]
    param([Alias("ComputerName")] [string[]] $hostnames = "localhost",
          [Alias("Credential")] [pscredential] [System.Management.Automation.Credential()] $cred = [pscredential]::empty)

    foreach ($hostname in $hostnames){
        if (Test-Connection -ComputerName $hostname -Count 1 -Quiet){
            $session = New-PSSession -ComputerName $hostname -Credential $cred -ErrorAction SilentlyContinue
            if ($session){
                Remove-PSSession -Session $session
                Write-Host "host: '$($hostname)' status: online, WinRM online"
            } else {
                Write-Host "host: '$($hostname)' status: online, WinRM failed"
            }
        } else {
            Write-Host "host: '$($hostname)' status: offline"
        }
    }
}

# Disable-DynamicDNSRegistraion -ComputerName ((Get-ADComputer -Filter * -SearchBase "CN=Computers,DC=CONTOSO,DC=COM").DNSHostName | where { $_ -ne $null })