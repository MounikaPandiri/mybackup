#!/usr/local/bin/perl
use diversifEye::TestGroup;
use strict;
use Getopt::Long;

# setup defaults
my $nfile1     = '';
my $nfile2     = '';
my $cfile    = '';
my @interface = '';
my $help     = 0;


GetOptions(
    'config=s' => \$cfile,
    'callerlist=s' => \$nfile1,
    'calleelist=s' => \$nfile2,
    'interface=s' => \@interface,
    'help!' => \$help,
) or die "Incorrect usage!\n";


if( $help ) {
    print "perl voip.pl <optional--args>";
} 

#Get the Host, Gateway and SIPProxy details
open FILE1, $cfile or die;
my %details;
while (my $line=<FILE1>) {
   chomp($line);
   (my $data1,my $data2) = split /:/, $line;
   $details{$data1} = $data2;
}

#Get the SIP number and password details
open FILE2, $nfile1 or die;
my %callerlist;
my %caller;
my %callerports;
my $i=0;
my $port="65530";
while (my $line=<FILE2>) {
   chomp($line);
   (my $word1,my $word2) = split /:/, $line;
   $callerlist{$word1} = $word2;
   $caller{$i} = $word1;
   $callerports{$word1}= $port;
   $port = $port - 2;
   $i++;
}

#Get the SIP number and password details
open FILE3, $nfile2 or die;
my %calleelist;
my %callee;
my %calleeports;
$i=0;
$port="65530";
while (my $line=<FILE3>) {
   chomp($line);
   (my $word1,my $word2) = split /:/, $line;
   $calleelist{$word1} = $word2;
   $callee{$i} = $word1;
   $calleeports{$word1}= $port;
   $port = $port - 2;
   $i++;
}


#Add a testgroup
my $Tg = diversifEye::TestGroup->new(
         name=>$details{"TestGroup_Name"},
         description=>"SIP Testgroup");

#Add Stream profile
my $Rsp = diversifEye::RtpStreamProfile->new(
          name=>"sipcodec",
          description=>"Voice only codec",
          used_for=>"Voice Only",
          rtp_data=>"Full Duplex");

my $Rspe = diversifEye::RtpStreamProfileEntry->new(
           name=>"Default G.711u (PCM)");

$Rsp->Add($Rspe);
$Tg->Add($Rsp);

#Configure Gateway host
my $GW = diversifEye::ExternalHost->new(
         name=>"Gateway",
         ip_address=>$details{"Gateway_IP"});

$Tg->Add($GW);

##Configure host 'UAC1'
my $Vh1 = diversifEye::DirectVirtualHost->new(
             name=>"UAC1",
             description=>"User agent client",
             service_state=>"In Service",
             ip_assignment_type=>"Static",
             gateway_host=>$GW,
             ip_address=>$details{"TVM1"},
             physical_interface=>$interface[1],
             mac_address_assignment_mode=>"Use MAC of Assigned Interface");
$Tg->Add($Vh1);

#Configure host 'UAC2'
my $Vh2 = diversifEye::DirectVirtualHost->new(
             name=>"UAC2",
             description=>"User agent client",
             service_state=>"In Service",
             ip_address=>$details{"TVM2"},
             ip_assignment_type=>"Static",
             gateway_host=>$GW,
             physical_interface=>$interface[2],
             mac_address_assignment_mode=>"Use MAC of Assigned Interface");

$Tg->Add($Vh2);

#Configure External SIPProxy
my $SIPProxy = diversifEye::ExternalHost->new(
             name=>"SIPProxy",
             ip_address=>$details{"SIPProxy_IP"});


$Tg->Add($SIPProxy);


#Configure External VoIP SIPProxy application
my $ExternalSIP = diversifEye::ExternalVoipSipProxy->new(
                 name=>"ExternalSIP",
                 description=>"External SIPProxy",
                 host=>$SIPProxy,
                 sip_domain_name=>"test.com");
$Tg->Add($ExternalSIP);

my $domain= '@test.com';
my $callersize=keys %caller;
my $rtpport=16384;
my $user=0;
my $str = "Caller";
my $callprefix = 'sip:';
my $portprefix=':';
my %UAC;
for ($user=0;$user<$callersize;$user++) {
    my $name= "$str$user";
    my $sipnum = $caller{$user};
    my $calluri = "$callprefix$callee{$user}$domain$portprefix$calleeports{$callee{$user}}";
    my $UAC = diversifEye::VoipUa->new(
                   name=>$name,
                   description=>"Caller",
                   host=>$Vh1,
                   transport_port=>$callerports{$sipnum}, #TODO
                   server=>$ExternalSIP,
                   use_client_ip_as_sip_domainname=>"false",
                   emulate_phone_type=>"Generic Phone",
                   sip_user_name=>$sipnum,     #TODO Enhance in using the command line arguments
                   sip_domain_name=>"test.com",
                   register_with_server=>"true",
                   transport_type=>"UDP",
                   rtp_ports=>$rtpport,
                   use_sip_username_as_password=>"false",
                   sip_password=>$callerlist{$sipnum}, #TODO
                   specify_sip_auth_username=>"true",
                   sip_auth_username=>"$caller{$user}$domain", #TODO
                   called_party_selection=>"Call URI",
                   call_uri=>$calluri, #TODO
                   stream_profile=>"sipcodec", #TODO verify
                   allow_ua_initiate_calls=>"true",
                   bhca=>"5",
                   average_hold_time=>"20",
                   average_hold_time_metric=>"secs",
                   media_type=>"voice");
    $Tg->Add($UAC);
    $rtpport = $rtpport + 2;
}

$str = "Callee";
$rtpport=16384;
my $calleesize=keys %callee;
for ($user=0;$user<$calleesize;$user++) {

    my $name= "$str$user";
    my $sipnum = $callee{$user};
    

    my $Callee = diversifEye::VoipUa->new(
                   name=>$name,
                   description=>"Callee",
                   host=>$Vh2,
                   transport_port=>$calleeports{$sipnum}, #TODO
                   server=>$ExternalSIP,
                   use_client_ip_as_sip_domainname=>"false",
                   emulate_phone_type=>"Generic Phone",
                   sip_user_name=>$sipnum,     #TODO Enhance in using the command line arguments
                   sip_domain_name=>"test.com",
                   register_with_server=>"true",
                   transport_type=>"UDP",
                   rtp_ports=>$rtpport,
                   use_sip_username_as_password=>"false",
                   sip_password=>$calleelist{$callee{$user}}, #TODO
                   specify_sip_auth_username=>"true",
                   sip_auth_username=>"$callee{$user}$domain", #TODO
                   called_party_selection=>"Call URI",
                   call_uri=>"", #TODO
                   stream_profile=>"sipcodec", #TODO verify
                   allow_ua_initiate_calls=>"false",
                   bhca=>"5",
                   average_hold_time=>"25",
                   average_hold_time_metric=>"secs",
                   media_type=>"voice");
    $Tg->Add($Callee);
    $rtpport = $rtpport + 2;
}

$Tg->End();
