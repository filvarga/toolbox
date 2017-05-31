# autor: Filip Varga

Import-Module network.ps1

function Remove-DuplicateDNSServerResourceRecord() {
    [CmdletBinding()]
    param([Alias("IPAddress")] [IPAddress] $address,
          [Alias("NetworkMask")] [IPAddress] $netmask,
          [Alias("ZoneName")] [string] $zone,
          [string] $filter = "")

    $network1 =  Get-NetworkAddress -IPAddress $address -NetworkMask $netmask
    $records = Get-DNSServerResourceRecord -Zone $zone -RRType A

    foreach ($n in ($records | Group-Object HostName)) {
        if ($n.Count -gt 1) {
            foreach ($record in $n.Group) {
                if ($record.HostName -match $filter) {
                    foreach ($resource in $record.RecordData) {
                        $network2 = Get-NetworkAddress -IPAddress $resource.IPv4Address -NetworkMask $netmask
        
                        if (-not $network1.Equals($network2)){
                                Remove-DnsServerResourceRecord -ZoneName $zone -RRType A -Name $record.HostName -RecordData $resource.IPv4Address -Force
                                Write-Host "removed record: $($record.HostName) $($resource.IPv4Address.IPAddressToString)"
                        }
                    }
                }
            }
        }
    }
}