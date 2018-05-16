function Get-RootID(){
    return (Get-ResourcePool -Name Resources).id
}

function Get-Children(){
    [CmdletBinding()]
    param(
        [Parameter(Mandatory = $true)]
        [System.Object]
        $Objects,

        [Parameter(Mandatory = $true)]
        [string]
        $ParentID
    )

    foreach ($object in $Objects){
        if ($object.ParentId -eq $ParentID){
            $object
        }
    }
}

function New-Tree(){
    [CmdletBinding()]
    param(
        [Parameter(Mandatory = $true)]
        [string]
        $ParentID
    )

    $children = @()

    foreach ($child in (Get-Children -Objects (Get-ResourcePool) -ParentID $ParentID)){
        $object = New-Object System.Object
        $object | Add-Member -Type NoteProperty -Name Self -Value $child
        $object | Add-Member -Type NoteProperty -Name Children -Value (New-Tree -ParentID $object.Self.Id)
        $children += $object
    }
    foreach ($child in (Get-Children -Objects (Get-VApp) -ParentID $ParentID)){
        $object = New-Object System.Object
        $object | Add-Member -Type NoteProperty -Name Self -Value $child
        $object | Add-Member -Type NoteProperty -Name Children -Value (New-Tree -ParentID $object.Self.Id)
        $children += $object
    }
    return $children
}

function Set-Document() {
    [CmdletBinding()]
    param(
        [Parameter(Mandatory = $true)]
        [string]
        $Tree,

        [Parameter(Mandatory = $true)]
        [Alias("RoyalFolder")]
        [System.Object]
        $Folder
    )

    foreach ($object in $Tree){
        $newFolder = New-RoyalObject -Folder $Folder -Type RoyalFolder -Name $object.Self.Name
        Set-Document -Tree $folder.Children -Folder $Folder
        
        foreach ($vm in ($object.Self | Get-VM)){
            $guestFamily = $vm.Guest.GuestFamily
            if ($guestFamily -eq 'windowsGuest'){
                $connection = New-RoyalObject -Folder $newFolder -Type RoyalRDSConnection -Name $vm.Name
            }
            elseif ($guestFamily -eq 'linuxGuest') {
                $connection = New-RoyalObject -Folder $newFolder -Type RoyalSSHConnection -Name $vm.Name
            }
            if ($connection) {
                $connection.Description  = $vm.Guest.OSFullName
                # TODO: vs $vm.Guest.IPAddress
                $connection.URI = $vm.Guest.HostName
                $connection.MAC = ($vm | Get-NetworkAdapter).MacAddress
                $connection.Notes = $vm.Notes
            }
        }
        #Set-RoyalObjectValue -Object $connection -Property ManagementEndpointFromParent -Value $true | Out-Null
        #Set-RoyalObjectValue -Object $connection -Property SecureGatewayFromParent -Value $true | Out-Null
        #$object = New-RoyalObject
    }
}

function New-Document() {
    [CmdletBinding()]
    param(
        [Paramenter(Mandatory = $true)]
        [Alias("FileName")]
        [string]
        $file
    )

    $username = $env:USERDOMAIN + '\' + $env:USERNAME
    $store = New-RoyalStore -UserName $username
    $doc = New-RoyalDocument -Store $store -Name 'VMware vCenter' -FileName $file

    $folder = New-RoyalObject -Folder $doc -Name 'Pripojenia' -Type RoyalFolder
    New-RoyalObject -Folder $doc -Name 'Oprávnenia' -Type RoyalFolder
    Set-Document -Tree (New-Tree -ParentID (Get-RootID)) -Folder $folder
}

function CreateRoyalFolderHierarchy(){
    param(
        [string]$folderStructure,
        [string]$splitter,
        $Folder
    )
    $currentFolder = $Folder

    $folderStructure -split $splitter | %{
        $folder = $_
        $existingFolder = Get-RoyalObject -Folder $currentFolder -Name $folder -Type RoyalFolder
        if($existingFolder){
            Write-Verbose "Folder $folder already exists - using it"
            $currentFolder = $existingFolder
        }
        else {
            Write-Verbose "Folder $folder does not exist - creating it"
            $newFolder= New-RoyalObject -Folder $currentFolder -Name $folder -Type RoyalFolder
            $currentFolder  = $newFolder
        }
    }
    return $currentFolder
}

$fileName = "outputcsv.rtsz" #relative to the current file-system directory
#if(Test-Path $fileName) {Remove-Item $fileName}


$store = New-RoyalStore -UserName "PowerShellUser"
$doc = New-RoyalDocument -Store $store -Name "Powershell import from CSV" -FileName $fileName
Import-CSV -Path servers.csv | %{
    $server = $_
    Write-Host "Importing $($server.Name)"

    $lastFolder = CreateRoyalFolderHierarchy -folderStructure $server.Folder -Splitter  "\/" -Folder $doc

    $newConnection = New-RoyalObject -Folder $lastFolder -Type RoyalRDSConnection -Name $server.Name
    $newConnection.URI = $server.URI
}

Out-RoyalDocument -Document $doc -FileName $fileName
