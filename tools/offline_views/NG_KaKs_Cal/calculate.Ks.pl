#calculate.Ks.pl
use strict;
# use warnings; # 注释掉警告，保持输出清爽

use Bio::SeqIO;
use Bio::Align::Utilities qw(aa_to_dna_aln);
use Bio::Seq::EncodedSeq;
use Bio::AlignIO;
use FindBin qw($Bin);
use lib "$Bin";
use SeqStatistics;

# ===============================================
# 接收参数 (由 Python tools.py 传入)
# ===============================================
my $dirname   = $ARGV[0]; # 临时文件夹名 (如 1_2)
my $Aspecies  = $ARGV[1]; # 物种标记 (如 1)
my $infile    = $ARGV[2]; # Block 文件绝对路径
my $fastafile = $ARGV[3]; # 合并后的 CDS Fasta 绝对路径
my $outfile   = $ARGV[4]; # 【修复1】直接接收绝对路径，不要加 ./ks/ 前缀！

# ===============================================
# 1. 读取 Fasta 序列到内存
# ===============================================
# print "Reading Fasta: $fastafile\n";
my %hash_seq;

# 检查文件是否存在
if (!-e $fastafile) {
    die "Error: Fasta file not found: $fastafile\n";
}

my $seq = Bio::SeqIO->new(-file => $fastafile, '-format' => 'fasta');
while(my $seqobj = $seq->next_seq()){
   $hash_seq{$seqobj->id} = $seqobj;
}

# ===============================================
# 2. 打开输入输出文件
# ===============================================
open(IN, $infile) or die "Cannot open block file $infile: $!.\n";
open(OUT, ">$outfile") or die "Cannot create output file $outfile: $!.\n";

# 确保临时目录存在
if (!-d $dirname) {
    mkdir $dirname; # 如果失败通常是因为文件夹已存在，忽略错误
}

# ===============================================
# 3. 循环处理每一对基因
# ===============================================
while(<IN>){
    chomp;
    $_ =~ s/[\r\n]//g; # 去除换行符
    next if /^\s*$/;   # 跳过空行
    
    # 【修复2】tools.py 生成的 block 文件只有两列
    my @array = split(/\s+/, $_);
    
    # 确保至少有两列
    if (scalar(@array) < 2) { next; }

    my $id1 = $array[0];
    my $id2 = $array[1]; # 【修复2】原代码是 array[2]，改为 array[1]

    # 自我比对跳过
    if ($id1 eq $id2) { next; }
    
    # 检查序列是否存在 (防止 Perl 报错崩溃)
    if (!exists $hash_seq{$id1} || !exists $hash_seq{$id2}) {
        # print "Warning: Sequence $id1 or $id2 not found in fasta.\n";
        next;
    }

    # print "Processing: $id1 - $id2\n";

    # 3.1 提取序列并翻译成蛋白
    my %dna_hash;
    $dna_hash{$id1} = $hash_seq{$id1};
    $dna_hash{$id2} = $hash_seq{$id2};

    my $prot_file = "$dirname/prot.fasta";
    my $prot = Bio::SeqIO->new(-file => ">$prot_file", -format => "fasta");
    $prot->write_seq($hash_seq{$id1}->translate());
    $prot->write_seq($hash_seq{$id2}->translate());

    # 3.2 调用 ClustalW 进行蛋白比对
    # 【修复3】给路径加引号，防止 Windows 路径含空格报错，加 -QUIET 减少日志
    system("clustalw2 \"$prot_file\" -QUIET");

    # ClustalW 默认生成 .aln 文件
    my $aln_file = "$dirname/prot.aln";
    
    if (-e $aln_file) {
        my $is_prot_aln = Bio::AlignIO->new(-file => $aln_file, -format => "CLUSTALW");
        my $prot_aln = $is_prot_aln->next_aln();

        # 3.3 蛋白比对回推 DNA 比对 (Codon Alignment)
        my $dna_aln = &aa_to_dna_aln($prot_aln, \%dna_hash);
        
        # 3.4 计算 Ka/Ks
        my $stats = new SeqStatistics;
        my $result = $stats->calc_all_KaKs_pairs($dna_aln);
        
        my ($Da, $Ds, $Dn, $N, $S) = (-2, -2, -2, 0, 0);

        for my $an (@$result) {
            for (keys %$an) {
                if($_ eq "D_n") { $Dn = $an->{$_}; }
                if($_ eq "D_s") { $Ds = $an->{$_}; }
                # if($_ eq "S")   { $S  = $an->{$_}; }
                # if($_ eq "N")   { $N  = $an->{$_}; }
            }
        }

        # 格式化输出
        if($Dn !~ /\d/) { $Dn = -2; }
        if($Ds !~ /\d/) { $Ds = -2; }

        print OUT "$id1\t$id2\t$Dn\t$Ds\n";
        
    } else {
        # print "Error: Alignment file not generated for $id1-$id2\n";
    }
}

close(IN);
close(OUT);
# print "Done.\n";