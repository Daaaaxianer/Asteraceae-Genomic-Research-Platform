from django.db import models
# Write by yuzijian. email: yuzijian1010@163.com

from django.db import models


class CollinearBlockPairs(models.Model):
    unique_id = models.CharField(max_length=50, primary_key=True)
    Query_Genome = models.CharField(max_length=50)
    Query_Chromosome = models.CharField(max_length=50)
    Reference_Genome = models.CharField(max_length=50)
    Th_ID = models.CharField(max_length=50)
    Number_matches = models.CharField(max_length=50)
    P_value = models.CharField(max_length=50)
    Chr_Chr = models.CharField(max_length=50)


class CollinearBlockDetail(models.Model):
    unique_id = models.CharField(max_length=50, primary_key=True)
    Number = models.CharField(max_length=50)
    Gene1 = models.CharField(max_length=50)
    Gene1_num = models.CharField(max_length=50)
    Gene2 = models.CharField(max_length=50)
    Gene2_num = models.CharField(max_length=50)
    Strand = models.CharField(max_length=50)



class TEModel(models.Model):
    hhh_number = models.AutoField(primary_key=True)  # 自增主键
    gene_id = models.CharField(max_length=50)
    start_position = models.CharField(max_length=50)
    end_position = models.CharField(max_length=50)
    te_class_1 = models.CharField(max_length=50)
    te_class_2 = models.CharField(max_length=50)
    te_class_3 = models.CharField(max_length=50)
    te_class_4 = models.CharField(max_length=50)
    sequence = models.TextField()

    class Meta:
        db_table = None  # 设置为 None，避免默认的表名生成规则

    def __init__(self, *args, **kwargs):
        sp_name = kwargs.pop('sp_name', None)  # 从参数中获取 sp_name
        if sp_name:
            self._meta.db_table = f'{sp_name}_TE_table'  # 设置表名
        super().__init__(*args, **kwargs)


# Hean的共线性列表
class HierarchicalAlignment_Hean(models.Model):
    hhh_number = models.IntegerField(primary_key=True)
    Hean_1 = models.CharField(max_length=20)
    Cobi_1 = models.CharField(max_length=20)
    Bial_1 = models.CharField(max_length=20)
    Bial_2 = models.CharField(max_length=20)
    Dapi_1 = models.CharField(max_length=20)
    Dapi_2 = models.CharField(max_length=20)
    Hetu_1 = models.CharField(max_length=20)
    Hetu_2 = models.CharField(max_length=20)
    Hetu_3 = models.CharField(max_length=20)
    Amtr_1 = models.CharField(max_length=20)
    Smso_1 = models.CharField(max_length=20)
    Smso_2 = models.CharField(max_length=20)
    Taer_1 = models.CharField(max_length=20)
    Fro_1 = models.CharField(max_length=20)
    Fso_1 = models.CharField(max_length=20)
    Ftr_1 = models.CharField(max_length=20)
    Fra_1 = models.CharField(max_length=20)
    Fli_1 = models.CharField(max_length=20)
    Stre_1 = models.CharField(max_length=20)
    Mimi_1 = models.CharField(max_length=20)
    Hean_2 = models.CharField(max_length=20)
    Cobi_2 = models.CharField(max_length=20)
    Bial_3 = models.CharField(max_length=20)
    Bial_4 = models.CharField(max_length=20)
    Dapi_3 = models.CharField(max_length=20)
    Dapi_4 = models.CharField(max_length=20)
    Hetu_4 = models.CharField(max_length=20)
    Hetu_5 = models.CharField(max_length=20)
    Hetu_6 = models.CharField(max_length=20)
    Amtr_2 = models.CharField(max_length=20)
    Smso_3 = models.CharField(max_length=20)
    Smso_4 = models.CharField(max_length=20)
    Taer_2 = models.CharField(max_length=20)
    Fro_2 = models.CharField(max_length=20)
    Fso_2 = models.CharField(max_length=20)
    Ftr_2 = models.CharField(max_length=20)
    Fra_2 = models.CharField(max_length=20)
    Fli_2 = models.CharField(max_length=20)
    Stre_2 = models.CharField(max_length=20)
    Mimi_2 = models.CharField(max_length=20)
    class Meta:
        db_table = 'Hierarchical_alignment_Hean_table'

class HierarchicalGene_Hean(models.Model):
    hhh_number = models.IntegerField(primary_key=True)
    sp_name = models.CharField(max_length=20)
    gene_id = models.CharField(max_length=20)
    chr_num = models.CharField(max_length=20)
    start = models.CharField(max_length=20)
    end = models.CharField(max_length=20)
    strand = models.CharField(max_length=1)
    class Meta:
        db_table = 'Hierarchical_genes_Hean_table'
    def __str__(self):
        return self.gene_id


# Eupl的共线性列表
class HierarchicalAlignment_Eupl(models.Model):
    hhh_number = models.IntegerField(primary_key=True)
    Eupl_1 = models.CharField(max_length=20)
    Eupl_2 = models.CharField(max_length=20)
    Nenu_1 = models.CharField(max_length=20)
    Nenu_2 = models.CharField(max_length=20)
    Tesi_1 = models.CharField(max_length=20)
    Tesi_2 = models.CharField(max_length=20)
    Tesi_3 = models.CharField(max_length=20)
    Tesi_4 = models.CharField(max_length=20)
    Busi_1 = models.CharField(max_length=20)
    Busi_2 = models.CharField(max_length=20)
    Vivi_1 = models.CharField(max_length=20)
    Vivi_2 = models.CharField(max_length=20)
    Vivi_3 = models.CharField(max_length=20)
    Nin_1 = models.CharField(max_length=20)
    Nin_2 = models.CharField(max_length=20)
    Nin_3 = models.CharField(max_length=20)
    Arla_1 = models.CharField(max_length=20)
    Arla_2 = models.CharField(max_length=20)
    Arla_3 = models.CharField(max_length=20)
    Arla_4 = models.CharField(max_length=20)
    Arla_5 = models.CharField(max_length=20)
    Arla_6 = models.CharField(max_length=20)
    Arla_7 = models.CharField(max_length=20)
    Arla_8 = models.CharField(max_length=20)
    Arla_9 = models.CharField(max_length=20)
    class Meta:
        db_table = 'Hierarchical_alignment_Eupl_table'

class HierarchicalGene_Eupl(models.Model):
    hhh_number = models.IntegerField(primary_key=True)
    sp_name = models.CharField(max_length=20)
    gene_id = models.CharField(max_length=20)
    chr_num = models.CharField(max_length=20)
    start = models.CharField(max_length=20)
    end = models.CharField(max_length=20)
    strand = models.CharField(max_length=1)
    class Meta:
        db_table = 'Hierarchical_genes_Eupl_table'
    def __str__(self):
        return self.gene_id

# Lssa_all的共线性列表
class HierarchicalAlignment_Lssa_all(models.Model):
    number = models.IntegerField(db_column='Number', primary_key=True)
    Arla_1 = models.CharField(max_length=20)
    Arla_2 = models.CharField(max_length=20)
    Arla_3 = models.CharField(max_length=20)
    Gehy_1 = models.CharField(max_length=20)
    Armi_1 = models.CharField(max_length=20)
    Sain_1 = models.CharField(max_length=20)
    Ceso_1 = models.CharField(max_length=20)
    Cati_1 = models.CharField(max_length=20)
    Ccar_1 = models.CharField(max_length=20)
    Cien_1 = models.CharField(max_length=20)
    Cich_1 = models.CharField(max_length=20)
    Lssa_1 = models.CharField(max_length=20)
    Laca_1 = models.CharField(max_length=20)
    Tako_1 = models.CharField(max_length=20)
    Tamo_1 = models.CharField(max_length=20)
    Pslu_1 = models.CharField(max_length=20)
    Lomi_1 = models.CharField(max_length=20)
    Lomi_2 = models.CharField(max_length=20)
    Enbr_1 = models.CharField(max_length=20)
    Ecan_1 = models.CharField(max_length=20)
    Soca_1 = models.CharField(max_length=20)
    Glco_1 = models.CharField(max_length=20)
    Artr_1 = models.CharField(max_length=20)
    Aary_1 = models.CharField(max_length=20)
    Aary_2 = models.CharField(max_length=20)
    Aann_1 = models.CharField(max_length=20)
    Chma_1 = models.CharField(max_length=20)
    Chmo_1 = models.CharField(max_length=20)
    Chmo_2 = models.CharField(max_length=20)
    Chmo_3 = models.CharField(max_length=20)
    Chla_1 = models.CharField(max_length=20)
    Chna_1 = models.CharField(max_length=20)
    Cind_1 = models.CharField(max_length=20)
    Pdy_1 = models.CharField(max_length=20)
    Cobi_1 = models.CharField(max_length=20)
    Hean_1 = models.CharField(max_length=20)
    Bial_1 = models.CharField(max_length=20)
    Bial_2 = models.CharField(max_length=20)
    Dapi_1 = models.CharField(max_length=20)
    Dapi_2 = models.CharField(max_length=20)
    Hetu_1 = models.CharField(max_length=20)
    Hetu_2 = models.CharField(max_length=20)
    Hetu_3 = models.CharField(max_length=20)
    Amtr_1 = models.CharField(max_length=20)
    Smso_1 = models.CharField(max_length=20)
    Smso_2 = models.CharField(max_length=20)
    Taer_1 = models.CharField(max_length=20)
    Fro_1 = models.CharField(max_length=20)
    Fso_1 = models.CharField(max_length=20)
    Ftr_1 = models.CharField(max_length=20)
    Fra_1 = models.CharField(max_length=20)
    Fli_1 = models.CharField(max_length=20)
    Stre_1 = models.CharField(max_length=20)
    Mimi_1 = models.CharField(max_length=20)
    Cobi_2 = models.CharField(max_length=20)
    Hean_2 = models.CharField(max_length=20)
    Bial_3 = models.CharField(max_length=20)
    Bial_4 = models.CharField(max_length=20)
    Dapi_3 = models.CharField(max_length=20)
    Dapi_4 = models.CharField(max_length=20)
    Hetu_4 = models.CharField(max_length=20)
    Hetu_5 = models.CharField(max_length=20)
    Hetu_6 = models.CharField(max_length=20)
    Amtr_2 = models.CharField(max_length=20)
    Smso_3 = models.CharField(max_length=20)
    Smso_4 = models.CharField(max_length=20)
    Taer_2 = models.CharField(max_length=20)
    Fro_2 = models.CharField(max_length=20)
    Fso_2 = models.CharField(max_length=20)
    Ftr_2 = models.CharField(max_length=20)
    Fra_2 = models.CharField(max_length=20)
    Fli_2 = models.CharField(max_length=20)
    Stre_2 = models.CharField(max_length=20)
    Mimi_2 = models.CharField(max_length=20)
    class Meta:
        db_table = 'Hierarchical_alignment_Lssa_all_table'

class HierarchicalGene_Lssa_all(models.Model):
    hhh_number = models.IntegerField(primary_key=True)
    sp_name = models.CharField(max_length=20)
    gene_id = models.CharField(max_length=20)
    chr_num = models.CharField(max_length=20)
    start = models.CharField(max_length=20)
    end = models.CharField(max_length=20)
    strand = models.CharField(max_length=1)
    class Meta:
        db_table = 'Hierarchical_genes_Lssa_all_table'
    def __str__(self):
        return self.gene_id

# Lssa_part的共线性列表
class HierarchicalAlignment_Lssa_part(models.Model):
    hhh_number = models.IntegerField(primary_key=True)
    Lssa = models.CharField(max_length=20)
    Aann = models.CharField(max_length=20)
    Arla = models.CharField(max_length=20)
    Armi = models.CharField(max_length=20)
    Artr_1 = models.CharField(max_length=20)
    Artr_2 = models.CharField(max_length=20)
    Hean = models.CharField(max_length=20)
    Cati = models.CharField(max_length=20)
    Ccar = models.CharField(max_length=20)
    Ceso = models.CharField(max_length=20)
    Chla = models.CharField(max_length=20)
    Chma = models.CharField(max_length=20)
    Chmo_1 = models.CharField(max_length=20)
    Chmo_2 = models.CharField(max_length=20)
    Chmo_3 = models.CharField(max_length=20)
    Chna = models.CharField(max_length=20)
    Cich = models.CharField(max_length=20)
    Cien = models.CharField(max_length=20)
    Cind = models.CharField(max_length=20)
    Ecan = models.CharField(max_length=20)
    Enbr = models.CharField(max_length=20)
    Glco = models.CharField(max_length=20)
    Heub = models.CharField(max_length=20)
    Laca = models.CharField(max_length=20)
    Lomi_1 = models.CharField(max_length=20)
    Lomi_2 = models.CharField(max_length=20)
    Pdy = models.CharField(max_length=20)
    Pslu = models.CharField(max_length=20)
    Sain = models.CharField(max_length=20)
    Sesq = models.CharField(max_length=20)
    Soca = models.CharField(max_length=20)
    Tako = models.CharField(max_length=20)
    Tamo = models.CharField(max_length=20)

    class Meta:
        db_table = 'Hierarchical_alignment_Lssa_part_table'

class HierarchicalGene_Lssa_part(models.Model):
    hhh_number = models.IntegerField(primary_key=True)
    sp_name = models.CharField(max_length=20)
    gene_id = models.CharField(max_length=20)
    chr_num = models.CharField(max_length=20)
    start = models.CharField(max_length=20)
    end = models.CharField(max_length=20)
    strand = models.CharField(max_length=1)

    class Meta:
        db_table = 'Hierarchical_genes_Lssa_part_table'

    def __str__(self):
        return self.gene_id

# Vivi的共线性列表
class HierarchicalAlignment_Vivi(models.Model):
    hhh_number = models.IntegerField(primary_key=True)
    Vivi_1 = models.CharField(max_length=20)
    Arla_1 = models.CharField(max_length=20)
    Armi_1 = models.CharField(max_length=20)
    Sain_1 = models.CharField(max_length=20)
    Ceso_1 = models.CharField(max_length=20)
    Cati_1 = models.CharField(max_length=20)
    Ccar_1 = models.CharField(max_length=20)
    Cien_1 = models.CharField(max_length=20)
    Cich_1 = models.CharField(max_length=20)
    Lssa_1 = models.CharField(max_length=20)
    Laca_1 = models.CharField(max_length=20)
    Tako_1 = models.CharField(max_length=20)
    Tamo_1 = models.CharField(max_length=20)
    Pslu_1 = models.CharField(max_length=20)
    Lomi_1 = models.CharField(max_length=20)
    Lomi_2 = models.CharField(max_length=20)
    Enbr_1 = models.CharField(max_length=20)
    Ecan_1 = models.CharField(max_length=20)
    Soca_1 = models.CharField(max_length=20)
    Glco_1 = models.CharField(max_length=20)
    Artr_1 = models.CharField(max_length=20)
    Aary_1 = models.CharField(max_length=20)
    Aary_2 = models.CharField(max_length=20)
    Aann_1 = models.CharField(max_length=20)
    Chma_1 = models.CharField(max_length=20)
    Chmo_1 = models.CharField(max_length=20)
    Chmo_2 = models.CharField(max_length=20)
    Chmo_3 = models.CharField(max_length=20)
    Chla_1 = models.CharField(max_length=20)
    Chna_1 = models.CharField(max_length=20)
    Cind_1 = models.CharField(max_length=20)
    Pdy_1 = models.CharField(max_length=20)
    Cobi_1 = models.CharField(max_length=20)
    Hean_1 = models.CharField(max_length=20)
    Bial_1 = models.CharField(max_length=20)
    Bial_2 = models.CharField(max_length=20)
    Dapi_1 = models.CharField(max_length=20)
    Dapi_2 = models.CharField(max_length=20)
    Hetu_1 = models.CharField(max_length=20)
    Hetu_2 = models.CharField(max_length=20)
    Hetu_3 = models.CharField(max_length=20)
    Amtr_1 = models.CharField(max_length=20)
    Smso_1 = models.CharField(max_length=20)
    Smso_2 = models.CharField(max_length=20)
    Taer_1 = models.CharField(max_length=20)
    Fro_1 = models.CharField(max_length=20)
    Fso_1 = models.CharField(max_length=20)
    Ftr_1 = models.CharField(max_length=20)
    Fra_1 = models.CharField(max_length=20)
    Fli_1 = models.CharField(max_length=20)
    Stre_1 = models.CharField(max_length=20)
    Mimi_1 = models.CharField(max_length=20)
    Cobi_2 = models.CharField(max_length=20)
    Hean_2 = models.CharField(max_length=20)
    Bial_3 = models.CharField(max_length=20)
    Bial_4 = models.CharField(max_length=20)
    Dapi_3 = models.CharField(max_length=20)
    Dapi_4 = models.CharField(max_length=20)
    Hetu_4 = models.CharField(max_length=20)
    Hetu_5 = models.CharField(max_length=20)
    Hetu_6 = models.CharField(max_length=20)
    Amtr_2 = models.CharField(max_length=20)
    Smso_3 = models.CharField(max_length=20)
    Smso_4 = models.CharField(max_length=20)
    Taer_2 = models.CharField(max_length=20)
    Fro_2 = models.CharField(max_length=20)
    Fso_2 = models.CharField(max_length=20)
    Ftr_2 = models.CharField(max_length=20)
    Fra_2 = models.CharField(max_length=20)
    Fli_2 = models.CharField(max_length=20)
    Stre_2 = models.CharField(max_length=20)
    Mimi_2 = models.CharField(max_length=20)
    Arla_2 = models.CharField(max_length=20)
    Armi_2 = models.CharField(max_length=20)
    Sain_2 = models.CharField(max_length=20)
    Ceso_2 = models.CharField(max_length=20)
    Cati_2 = models.CharField(max_length=20)
    Ccar_2 = models.CharField(max_length=20)
    Cien_2 = models.CharField(max_length=20)
    Cich_2 = models.CharField(max_length=20)
    Lssa_2 = models.CharField(max_length=20)
    Laca_2 = models.CharField(max_length=20)
    Tako_2 = models.CharField(max_length=20)
    Tamo_2 = models.CharField(max_length=20)
    Pslu_2 = models.CharField(max_length=20)
    Lomi_3 = models.CharField(max_length=20)
    Lomi_4 = models.CharField(max_length=20)
    Enbr_2 = models.CharField(max_length=20)
    Ecan_2 = models.CharField(max_length=20)
    Soca_2 = models.CharField(max_length=20)
    Glco_2 = models.CharField(max_length=20)
    Artr_2 = models.CharField(max_length=20)
    Aary_3 = models.CharField(max_length=20)
    Aary_4 = models.CharField(max_length=20)
    Aann_2 = models.CharField(max_length=20)
    Chma_2 = models.CharField(max_length=20)
    Chmo_4 = models.CharField(max_length=20)
    Chmo_5 = models.CharField(max_length=20)
    Chmo_6 = models.CharField(max_length=20)
    Chla_2 = models.CharField(max_length=20)
    Chna_2 = models.CharField(max_length=20)
    Cind_2 = models.CharField(max_length=20)
    Pdy_2 = models.CharField(max_length=20)
    Cobi_3 = models.CharField(max_length=20)
    Hean_3 = models.CharField(max_length=20)
    Bial_5 = models.CharField(max_length=20)
    Bial_6 = models.CharField(max_length=20)
    Dapi_5 = models.CharField(max_length=20)
    Dapi_6 = models.CharField(max_length=20)
    Hetu_7 = models.CharField(max_length=20)
    Hetu_8 = models.CharField(max_length=20)
    Hetu_9 = models.CharField(max_length=20)
    Amtr_3 = models.CharField(max_length=20)
    Smso_5 = models.CharField(max_length=20)
    Smso_6 = models.CharField(max_length=20)
    Taer_3 = models.CharField(max_length=20)
    Fro_3 = models.CharField(max_length=20)
    Fso_3 = models.CharField(max_length=20)
    Ftr_3 = models.CharField(max_length=20)
    Fra_3 = models.CharField(max_length=20)
    Fli_3 = models.CharField(max_length=20)
    Stre_3 = models.CharField(max_length=20)
    Mimi_3 = models.CharField(max_length=20)
    Cobi_4 = models.CharField(max_length=20)
    Hean_4 = models.CharField(max_length=20)
    Bial_7 = models.CharField(max_length=20)
    Bial_8 = models.CharField(max_length=20)
    Dapi_7 = models.CharField(max_length=20)
    Dapi_8 = models.CharField(max_length=20)
    Hetu_10 = models.CharField(max_length=20)
    Hetu_11 = models.CharField(max_length=20)
    Hetu_12 = models.CharField(max_length=20)
    Amtr_4 = models.CharField(max_length=20)
    Smso_7 = models.CharField(max_length=20)
    Smso_8 = models.CharField(max_length=20)
    Taer_4 = models.CharField(max_length=20)
    Fro_4 = models.CharField(max_length=20)
    Fso_4 = models.CharField(max_length=20)
    Ftr_4 = models.CharField(max_length=20)
    Fra_4 = models.CharField(max_length=20)
    Fli_4 = models.CharField(max_length=20)
    class Meta:
        db_table = 'Hierarchical_alignment_Vivi_table'

class HierarchicalGene_Vivi(models.Model):
    chromosome = models.CharField(max_length=20)
    gene_id = models.CharField(max_length=20)
    chr_num = models.CharField(max_length=20)
    start = models.CharField(max_length=20)
    end = models.CharField(max_length=20)
    strand = models.CharField(max_length=1)

    class Meta:
        db_table = 'Hierarchical_genes_Vivi_table'

    def __str__(self):
        return self.gene_id

class Genetype_table(models.Model):
    hhh_number = models.IntegerField(primary_key=True)
    sp_name = models.CharField(max_length=20)
    gene1 = models.CharField(max_length=255, blank=True, null=True)
    location1 = models.CharField(max_length=255, blank=True, null=True)
    gene2 = models.CharField(max_length=255, blank=True, null=True)
    location2 = models.CharField(max_length=255, blank=True, null=True)
    e_value = models.CharField(db_column='e-value', max_length=255, blank=True, null=True)  # Field renamed to remove unsuitable characters.
    type = models.CharField(max_length=255, blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'Genetype_table'


class TfPfamTable(models.Model):
    species = models.CharField(max_length=255, blank=True, null=True)
    type = models.CharField(max_length=255, blank=True, null=True)
    family = models.CharField(max_length=255, blank=True, null=True)
    gene_id = models.CharField(max_length=255, blank=True, null=True)
    hmm_acc = models.CharField(max_length=255, blank=True, null=True)
    hmm_name = models.CharField(max_length=255, blank=True, null=True)
    score = models.CharField(max_length=255, blank=True, null=True)
    clan = models.CharField(max_length=255, blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'TF_pfam_table'

class HierarchicalGene(models.Model):
    chromosome = models.CharField(max_length=255, blank=True, null=True)
    start = models.CharField(max_length=255, blank=True, null=True)
    end = models.CharField(max_length=255, blank=True, null=True)
    strend = models.CharField(max_length=255, blank=True, null=True)
    old_gene = models.CharField(max_length=255, blank=True, null=True)
    new_gene = models.CharField(max_length=255, blank=True, null=True)
    num = models.CharField(max_length=255, blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'Hierarchicalgene'

class EventGenesTable(models.Model):
    hhh_number = models.IntegerField(blank=True, null=True)
    gene1 = models.CharField(max_length=255, blank=True, null=True)
    gene2 = models.CharField(max_length=255, blank=True, null=True)
    event = models.CharField(max_length=255, blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'Event_genes_table'
