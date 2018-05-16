

function Get-VirtualMachine() {
    [CmdletBinding()]
    param([Alias("IPAddress")] [IPAddress] $address)
    foreach ($vm in (Get-VM)){
        if ($vm.Guest.IPAddress.Contains($address.ToString())){
            return $vm
        }
    }
}

function Get-VirtualMachine2() {
    [CmdletBinding()]
    param(
        [Parameter(Mandatory = $true, ParameterSetName = 'ByAddress')]
        [Alias("IPAddress")]
        [IPAddress]
        $address,

        [Parameter(Mandatory = $true, ParameterSetName = 'ByDns')]
        [Alias("DnsName")]
        [string]
        $hostname
        )

    if ($PSCmdlet.ParameterSetName -eq 'ByDns'){
        $address = Resolve-DnsName $hostname -QuickTimeout 10
    }

    foreach ($vm in (Get-VM)){
        if ($vm.Guest.IPAddress.Contains($address.ToString())){
            return $vm
        }
    }
}

# Open-VMConsoleWindow

# Connect-VirtualMachine
# Start-Process "$env:windir\system32\mstsc.exe" -ArgumentList "/v:$machinename"
# Import-Module "${env:ProgramFiles(x86)}\code4ward.net\Royal TS V4\RoyalDocument.PowerShell.dll" 

#$username = ($env:USERDOMAIN + '\' + $env:USERNAME)
#$store =  $store = New-RoyalStore -UserName $username
#$royalDocument = Open-RoyalDocument -FileName $filename -Store $store -Password (Get-Credential $usnerma).Password