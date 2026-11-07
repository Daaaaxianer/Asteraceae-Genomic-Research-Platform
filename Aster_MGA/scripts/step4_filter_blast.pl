#!/usr/bin/perl
# Step 4: keep only the BLAST hits whose gene pair appears in the mc table.
#
# Usage: perl step4_filter_blast.pl IN.mc.txt FULL.blast OUT.new.blast
# Example:
#   perl scripts/step4_filter_blast.pl mc_table/Elu_v_Ddev.mc.txt \
#        blastp/Elu_Ddev.blast mc_table/Elu_Ddev.new.blast
use strict;

die "Usage: perl $0 IN.mc.txt FULL.blast OUT.new.blast\n" if @ARGV < 3;
my ($mc_file, $blast_file, $out_file) = @ARGV;
open(IN1, $mc_file) or die "cannot open $mc_file due to $!\n";
open(BLAST, $blast_file) or die "cannot open $blast_file due to $!\n";
open(OUT, ">", $out_file) or die "cannot open $out_file due to $!\n";

my %hash;
while (<IN1>) {
    chomp;
    s/\r//g;
    s/\s+/./g;
    s/,/\t/g;
    s/\t\d//;          # drop the trailing depth column
    my @arr = split(/\t/, $_);
    foreach my $a (@arr) {
        if ($a =~ /\d+g\d+/) {
            $hash{ $arr[0] . "\t" . $a } = 1;
        }
    }
}
while (<BLAST>) {
    chomp;
    s/\r//g;
    my @array = split(/\t/, $_);
    my $c = $array[0] . "\t" . $array[1];
    print OUT "$_\n" if exists $hash{$c};
}
close IN1;
close BLAST;
close OUT;
