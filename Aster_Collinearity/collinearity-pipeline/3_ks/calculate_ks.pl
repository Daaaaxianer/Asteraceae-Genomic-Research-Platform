#!/usr/bin/perl
# Calculate Dn and Ds for every gene pair of a ColinearScan block file.
#
# Usage: perl calculate_ks.pl TMPDIR SPECIES1 BLOCK_FILE CDS_FASTA OUT_FILE
#   TMPDIR     existing directory for the temporary ClustalW files
#   SPECIES1   only block lines that contain this species prefix are used
#   BLOCK_FILE ColinearScan *.block.rr.txt
#   CDS_FASTA  CDS sequences of all genes in the block file
#   OUT_FILE   output, one line per pair: id1  id2  Dn  Ds  (-2 = not calculated)
# Normally called by run_ks.py. Needs BioPerl and clustalw2.
use strict;

use Bio::SeqIO;
use Bio::Align::Utilities qw(aa_to_dna_aln);
use Bio::Seq::EncodedSeq;
use Bio::AlignIO;

use FindBin qw($Bin);
use lib "$Bin";
use SeqStatistics;

#use Bio::Tools::Run::Alignment::Clustalw;
#############################################

die "Usage: perl $0 TMPDIR SPECIES1 BLOCK_FILE CDS_FASTA OUT_FILE\n" if @ARGV < 5;
my $dirname = $ARGV[0];
my $Aspecies="$ARGV[1]";
my $infile="$ARGV[2]";

# print "\n\n\n\n\n\n";
# print "################################"."\n\n";
# print "Wangjp tells you that you need to pay attention before running the program:"."\n";
# print "\n\n";
# print "You need to prepare two files"."\n";
# print "\n\n";
# print "1:  pair file---two genes in one line,can name ***_pairs.txt"."\n";
# print "2:  CDS fasta file---cds fasta sequence that include in pair file, must name ***_pair.fasta, same as pair file"."\n";
# print "\n\n";
# print "RUN THE PROGRAM COMMAND:"."\n";
# print "\n";
# print "perl calculate.Ks.pl ***_pairs.txt"."\n";

# print "BEGIN START RUN, wait ............"."\n";
# print "\n\n\n\n\n";
# print "######################################"."\n";
#############################################

my $input = "$infile";##############################
open(IN, $input) or die "cannot open block files $input due to $!.\n";

my @arr = split(/\./,$input);
my $fastafile = "$ARGV[3]";
my %hash_seq;
my $seq=Bio::SeqIO -> new(-file =>$fastafile, '-format' => 'fasta');#############################
while(my $seqobj = $seq -> next_seq()){
   $hash_seq{$seqobj->id}=$seqobj;
}
my @array = split(/\./, $input);
my $output = $ARGV[4];
open(OUT, ">".$output) or die "cannot open outfile $output due to $!.\n";

my @temp;
my $colgeneno;
my $blockno = 0;
while(<IN>){
   $_ =~ s/[\n\r]//g;

print $_."\n";
if ($_ !~/$Aspecies/){
	#print OUT "$_\n";
	next;}
my @array = split(/\s+/,$_);

my $id1 = $array[0];
my $id2 = $array[2];

# print "my pair is=====================".$id1." ".$id2."\n";

   #if($_ =~/^[#>]/){next;}
   #my @array=split/\s+/,$_;
   #my ($id1,$id2);
   #if($#array<1){next;}
   #if($#array==1){
   #   if($array[0]=~ /^\w+\d+[gG]\d+/ && $array[1]=~ /^\w+\d+[gG]\d+/){
	# ($id1,$id2) = @array[0,1];
     # }
      #else{next;}   
   #}
   #if($#array >=1){
   #   if($array[0]=~ /^\w+\d+[gG]\d+/ && $array[1]=~ /^\w+\d+[gG]\d+/){
	# ($id1,$id2) = @array[0,1];
      #}
      #else{next;}       
   #}
   if ($id1 eq $id2){next;}
   my %dna_hash;
   print "$id1\t$id2\n";
   $dna_hash{$id1}=$hash_seq{$id1};
   $dna_hash{$id2}=$hash_seq{$id2};
   my $prot = Bio::SeqIO -> new(-file=> ">./$dirname/prot.fasta", -format=>"fasta");
   $prot -> write_seq($hash_seq{$id1} -> translate());
   $prot -> write_seq($hash_seq{$id2} -> translate());
   

   system("clustalw2 $dirname/prot.fasta");
   my $is_prot_aln = Bio::AlignIO -> new(-file=>"./$dirname/prot.aln", -format=>"CLUSTALW");
   my $prot_aln = $is_prot_aln -> next_aln();
   #system("rm prot.fasta prot.aln prot.dnd");   
   my $dna_aln = &aa_to_dna_aln($prot_aln, \%dna_hash);         
   my $stats = new SeqStatistics;
   my $result = $stats->calc_all_KaKs_pairs($dna_aln);
   my ($Da, $Ds, $Dn, $N, $S, $S_d, $N_d);
   for my $an (@$result)
   {
     for (sort keys %$an )
     {
          next if /Seq/;
          if($_ eq "D_n"){$Dn = $an->{$_}};
          if($_ eq "D_s"){$Ds = $an->{$_}};
          if($_ eq "S_d"){$S_d = $an->{$_};}
          if($_ eq "N_d"){$N_d = $an->{$_};}
          if($_ eq "S"){$S = $an->{$_};}
          if($_ eq "N"){$N = $an->{$_};}

     }
   }

   if($Dn !~ /\d/){$Dn = -2;}
   if($Ds !~ /\d/){$Ds = -2;}
  
   my $length1= length($dna_hash{$id1} -> seq);
   my $length2= length($dna_hash{$id2} -> seq);
   print OUT $id1."\t".$id2."\t".$Dn."\t".$Ds."\n";
}
close(IN);
close(OUT);

########################################
#######################################
# print "\n\n\n\n";
# print "********************************"."\n\n";
# print "HAVE DONE!!!!!"."\n";
# print "\n\n";
# #print "Writen by Jinpeng Wang"."\n";
# print "\n\n";
# print "Jinpeng!"."\n";
# print "\n\n";
# print "********************************"."\n\n";
# print "\n\n\n\n";
#######################################
#######################################
