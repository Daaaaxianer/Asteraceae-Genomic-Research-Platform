let jsTree = new JsTree($('#container'));
let data = [
    {
        "id": 9,
        "parentId": 0,
        "text": "Fabaceae"
    },
    {
        "id": 1,
        "parentId": 0,
        "text": "Papilionoideae",
        "child": [
            {
                "id": 2,
                "parentId": 1,
                "text": "Abrus Adans",
                "child": [
                    {
                        "id": 3,
                        "parentId": 2,
                        "text": "<i><a href='Apr'>Abrus precatorius</a></i>"
                    }
                ]
            },
            {
                "id": 2,
                "parentId": 1,
                "text": " Aeschynomene",
                "child": [
                    {
                        "id": 3,
                        "parentId": 2,
                        "text": "<a href='Aev'><i>Aeschynomene evenia</i></a>"
                    }
                ]
            },
            {
                "id": 2,
                "parentId": 1,
                "text": " Vicia",
                "child": [
                    {
                        "id": 3,
                        "parentId": 2,
                        "text": "<a href='Vfa'><i>Vicia faba</i></a>"
                    }
                ]
            },
            {
                "id": 2,
                "parentId": 1,
                "text": "Ammopiptanthus Cheng f",
                "child": [
                    {
                        "id": 3,
                        "parentId": 2,
                        "text": "<a href='Ana'><i>Ammopiptanthus nanus</i></a>"
                    }
                ]
            },
            {
                "id": 2,
                "parentId": 1,
                "text": "Macrotyloma Verdc",
                "child": [
                    {
                        "id": 3,
                        "parentId": 2,
                        "text": "<a href='Mun'><i>Macrotyloma uniflorum</i></a>"
                    }
                ]
            },
            {
                "id": 2,
                "parentId": 1,
                "text": "Abrus",
                "child": [
                    {
                        "id": 3,
                        "parentId": 2,
                        "text": "<a href='Ame'><i>Abrus melanospermus</i></a>"
                    }
                ]
            },
            {
                "id": 2,
                "parentId": 1,
                "text": "Amphicarpaea Elliot",
                "child": [
                    {
                        "id": 3,
                        "parentId": 2,
                        "text": "<a href='Aed'>Amphicarpaea edgeworthii</a>"
                    }
                ]
            },
            {
                "id": 2,
                "parentId": 1,
                "text": "Arachis",
                "child": [
                    {
                        "id": 3,
                        "parentId": 2,
                        "text": "<a href='Adu'>Arachis duranensis</a>"
                    },
                    {
                        "id": 3,
                        "parentId": 2,
                        "text": "<a href='Ahy'>Arachis hypogaea</a>"
                    },
                    {
                        "id": 3,
                        "parentId": 2,
                        "text": "<a href='Aip'>Arachis ipaensis</a>"
                    },
                    {
                        "id": 3,
                        "parentId": 2,
                        "text": "<a href='Amo'>Arachis monticola</a>"
                    }

                ]
            },
            {
                "id": 2,
                "parentId": 1,
                "text": "Astragalus",
                "child": [
                    {
                        "id": 3,
                        "parentId": 2,
                        "text": "<a href='Asi'>Astragalus sinicus</a>"
                    }
                ]
            },
            {
                "id": 2,
                "parentId": 1,
                "text": "Cajanus DC",
                "child": [
                    {
                        "id": 3,
                        "parentId": 2,
                        "text": "<a href='Cca'>Cajanus cajan</a>"
                    }
                ]
            },
            {
                "id": 2,
                "parentId": 1,
                "text": "Cicer",
                "child": [
                    {
                        "id": 3,
                        "parentId": 2,
                        "text": "<a href='Car'>Cicer arietinum</a>"
                    },
                    {
                        "id": 3,
                        "parentId": 2,
                        "text": "<a href='Cre'>Cicer reticulatum </a>"
                    },
                ]
            },
            {
                "id": 2,
                "parentId": 1,
                "text": "Dalbergia . f. nom. conserv.",
                "child": [
                    {
                        "id": 3,
                        "parentId": 2,
                        "text": "<a href='Dod'>Dalbergia odorifera</a>"
                    }
                ]
            },
            {
                "id": 2,
                "parentId": 1,
                "text": "Glycine",
                "child": [
                    {
                        "id": 3,
                        "parentId": 2,
                        "text": "<a href='Gla'>Glycine latifolia</a>"
                    },
                    {
                        "id": 3,
                        "parentId": 2,
                        "text": "<a href='Gma'>Glycine max</a>"
                    },
                    {
                        "id": 3,
                        "parentId": 2,
                        "text": "<a href='Gso'>Glycine soja</a>"
                    }
                ]
            },
            {
                "id": 2,
                "parentId": 1,
                "text": "Glycyrrhiza",
                "child": [
                    {
                        "id": 3,
                        "parentId": 2,
                        "text": "<a href='Gur'>Glycyrrhiza uralensis</a>"
                    }
                ]
            },
            {
                "id": 2,
                "parentId": 1,
                "text": "Lablab Adans",
                "child": [
                    {
                        "id": 3,
                        "parentId": 2,
                        "text": "<a href='Lpu'>Lablab purpureus</a>"
                    }
                ]
            },
            {
                "id": 2,
                "parentId": 1,
                "text": "Lupinus",
                "child": [
                    {
                        "id": 3,
                        "parentId": 2,
                        "text": "<a href='Lal'>Lupinus albus</a>"
                    },
                    {
                        "id": 3,
                        "parentId": 2,
                        "text": "<a href='Lan'>Lupinus angustifolius</a>"
                    }
                ]
            },
            {
                "id": 2,
                "parentId": 1,
                "text": "Mallotus Lour",
                "child": [
                    {
                        "id": 3,
                        "parentId": 2,
                        "text": "<a href='Lja'>Lotus japonicus</a>"
                    }
                ]
            },
            {
                "id": 2,
                "parentId": 1,
                "text": "Medicago",
                "child": [
                    {
                        "id": 3,
                        "parentId": 2,
                        "text": "<a href='Mpo'>Medicago polymorpha</a>"
                    },
                    {
                        "id": 3,
                        "parentId": 2,
                        "text": "<a href='Mru'>Medicago ruthenica</a>"
                    },
                    {
                        "id": 3,
                        "parentId": 2,
                        "text": "<a href='Msa'>Medicago sativa</a>"
                    },
                    {
                        "id": 3,
                        "parentId": 2,
                        "text": "<a href='Mtr'>Medicago truncatula</a>"
                    }
                ]
            },
            {
                "id": 2,
                "parentId": 1,
                "text": "Melilotus Miller",
                "child": [
                    {
                        "id": 3,
                        "parentId": 2,
                        "text": "<a href='Mal'>Melilotus albus</a>"
                    }
                ]
            },
            {
                "id": 2,
                "parentId": 1,
                "text": "Nissolia",
                "child": [
                    {
                        "id": 3,
                        "parentId": 2,
                        "text": "<a href='Nsc'>Nissolia schotti</a>"
                    }
                ]
            },
            {
                "id": 2,
                "parentId": 1,
                "text": "Phaseolus",
                "child": [
                    {
                        "id": 3,
                        "parentId": 2,
                        "text": "<a href='Pac'>Phaseolus acutifolius</a>"
                    },
                    {
                        "id": 3,
                        "parentId": 2,
                        "text": "<a href='Plu'>Phaseolus lunatus</a>"
                    },
                    {
                        "id": 3,
                        "parentId": 2,
                        "text": "<a href='Pvu'>Phaseolus vulgaris</a>"
                    }
                ]
            },
            {
                "id": 2,
                "parentId": 1,
                "text": "Pisum",
                "child": [
                    {
                        "id": 3,
                        "parentId": 2,
                        "text": "<a href='Psa'>Pisum sativum</a>"
                    }
                ]
            },
            {
                "id": 2,
                "parentId": 1,
                "text": "Pongamia Vent",
                "child": [
                    {
                        "id": 3,
                        "parentId": 2,
                        "text": "<a href='Ppi'>Pongamia pinnata</a>"
                    }
                ]
            },
            {
                "id": 2,
                "parentId": 1,
                "text": "Pueraria DC",
                "child": [
                    {
                        "id": 3,
                        "parentId": 2,
                        "text": "<a href='Pmo'><i>Pueraria montana</i></a>"
                    }
                ]
            },
            {
                "id": 2,
                "parentId": 1,
                "text": "Sophora",
                "child": [
                    {
                        "id": 3,
                        "parentId": 2,
                        "text": "<a href='Sja'><i>Styphnolobium japonicum</i></a>"
                    }
                ]
            },
            {
                "id": 2,
                "parentId": 1,
                "text": "Spatholobus Hassk",
                "child": [
                    {
                        "id": 3,
                        "parentId": 2,
                        "text": "<a href='Ssu'><i>Spatholobus suberectus</i></a>"
                    }
                ]
            },
            {
                "id": 2,
                "parentId": 1,
                "text": "Trifolium",
                "child": [
                    {
                        "id": 3,
                        "parentId": 2,
                        "text": "<a href='Toc'><i>Trifolium occidentale</i></a>"
                    },
                    {
                        "id": 3,
                        "parentId": 2,
                        "text": "<a href='Tpa'><i>Trifolium pallescens</i></a>"
                    },
                    {
                        "id": 3,
                        "parentId": 2,
                        "text": "<a href='Tpr'><i>Trifolium pratense</i></a>"
                    },
                    {
                        "id": 3,
                        "parentId": 2,
                        "text": "<a href='Tre'><i>Trifolium repens</i></a>"
                    },
                    {
                        "id": 3,
                        "parentId": 2,
                        "text": "<a href='Tsu'><i>Trifolium subterraneum</i></a>"
                    }
                ]
            },
            {
                "id": 2,
                "parentId": 1,
                "text": "Vicia",
                "child": [
                    {
                        "id": 3,
                        "parentId": 2,
                        "text": "<a href='Vsa'><i>Vicia sativa</i></a>"
                    }
                ]
            },
            {
                "id": 2,
                "parentId": 1,
                "text": "Vigna Savi",
                "child": [
                    {
                        "id": 3,
                        "parentId": 2,
                        "text": "<a href='Van'><i>Vigna angularis</i></a>"
                    },
                    {
                        "id": 3,
                        "parentId": 2,
                        "text": "<a href='Vmu'><i>Vigna mungo</i></a>"
                    },
                    {
                        "id": 3,
                        "parentId": 2,
                        "text": "<a href='Vra'><i>Vigna radiata</i></a>"
                    },
                    {
                        "id": 3,
                        "parentId": 2,
                        "text": "<a href='Vsu'><i>Vigna subterranea</i></a>"
                    },
                    {
                        "id": 3,
                        "parentId": 2,
                        "text": "<a href='Vum'><i>Vigna umbellata</i></a>"
                    },
                    {
                        "id": 3,
                        "parentId": 2,
                        "text": "<a href='Vun'><i>Vigna unguiculata</i></a>"
                    },
                    {
                        "id": 3,
                        "parentId": 2,
                        "text": "<a href='Vma'><i>Vigna marina</i></a>"
                    }
                ]
            }
        ]
    },
    {
        "id": 6,
        "parentId": 0,
        "text": "Caesalpinioideae",
        "child": [
            {
                "id": 4,
                "parentId": 6,
                "text": "Entada Adans. nom. cons",
                "child": [
                    {
                        "id": 3,
                        "parentId": 2,
                        "text": "<a href='Eph'><i>Entada phaseoloides</i></a>"
                    }
                ]
            },
            {
                "id": 4,
                "parentId": 6,
                "text": "Acacia Mill",
                "child": [
                    {
                        "id": 3,
                        "parentId": 2,
                        "text": "<a href='Fal'><i>Faidherbia albida</i></a>"
                    }
                ]
            },
            {
                "id": 4,
                "parentId": 6,
                "text": "Mimosa",
                "child": [
                    {
                        "id": 3,
                        "parentId": 2,
                        "text": "<a href='Mpu'><i>Mimosa pudica</i></a>"
                    }
                ]
            },
            {
                "id": 4,
                "parentId": 6,
                "text": "Cercis",
                "child": [
                    {
                        "id": 3,
                        "parentId": 2,
                        "text": "<a href='Cfa'><i>Chamaecrista fasciculata</i></a>"
                    }
                ]
            },
            {
                "id": 4,
                "parentId": 6,
                "text": "Bauhinia",
                "child": [
                    {
                        "id": 3,
                        "parentId": 2,
                        "text": "<a href='Sto'><i>Senna tora</i></a>"
                    }
                ]
            }
        ]
    },
    {
        "id": 6,
        "parentId": 0,
        "text": "Detarioideae",
        "child": [
            {
                "id": 4,
                "parentId": 6,
                "text": "Sindora Miq",
                "child": [
                     {
                        "id": 3,
                        "parentId": 2,
                        "text": "<a href='Sgl'><i>Sindora glabra</i></a>"
                    },
                ]
            },
            {
                "id": 4,
                "parentId": 6,
                "text": "Tamarindus",
                "child": [
                     {
                        "id": 3,
                        "parentId": 2,
                        "text": "<a href='Tin'><i>Tamarindus indica</i></a>"
                    },
                ]
            }
        ]
    },
    {
        "id": 6,
        "parentId": 0,
        "text": "Cercidoideae",
        "child": [
            {
                "id": 4,
                "parentId": 6,
                "text": "Subgen. Bauhinia",
                "child": [
                    {
                        "id": 3,
                        "parentId": 2,
                        "text": "<a href='Bva'><i>Bauhinia variegata</i></a>"
                    }
                ]
            },
            {
                "id": 4,
                "parentId": 6,
                "text": "Cercis",
                "child": [
                    {
                        "id": 3,
                        "parentId": 2,
                        "text": "<a href='Ccan'><i>Cercis canadensis</i></a>"
                    }
                ]
            },
        ]
    }
]

jsTree.init({ data: data,isOpenAll:true, searchInput:$('#txt_seach'), childrenField: "child", value: "id", text: "text" ,clickCallback:(e)=>{
    console.log(e)
}});
$('#openAll').click(function(){
    jsTree.openAll();
})
$('#closeAll').click(function(){
    jsTree.closeAll();
})