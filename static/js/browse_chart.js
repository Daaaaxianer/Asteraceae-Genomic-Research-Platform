var chartDom = document.getElementById('containers');
var myChart = echarts.init(chartDom);
var option;

myChart.showLoading();

var data = {
    "name": "CGRPOEE",
    "children": [
        {
            "name": "  ",
            "children": [
                {"name": "{a|Gamma    core Eudicots}",
                "children": [
                    {"name": "{a|V. vinifera}"},

                ]
                },
                {"name": "{b|T-Beta   T-Alpha   Trochodendrales}",
                    "children": [
                        {"name": "{b|T. sinense}"},
                    ]
                },

           ]
        },
        {
            "name": "{c|RCT   Ranunculaes}",
            "children": [
                {
                    "name": "{c|PST   Papaveraceaes}",
                    "children": [
                        {"name" : "{c|P. somniferum}"}
                    ]
                },
                {
                    "name": "{d|Ranunculae}",
                    "children": [
                        {"name" : "{d|C. chinensis}"},
                        {"name" : "{d|A. coerulea}"}
                    ]
                },
            ]
        }
    ]
};

myChart.hideLoading();
data.label={color: 'red',
			fontSize: '20'};
myChart.setOption(option = {
    tooltip: {
        trigger: 'item',
        triggerOn: 'mousemove'
    },
    // legend: {
    //     top: '2%',
    //     left: '3%',
    //     orient: 'vertical',
    //     data: [{
    //         name: 'tree1',
    //         icon: 'rectangle'
    //     },
    //     {
    //         name: 'tree2',
    //         icon: 'rectangle'
    //     }],
    //     borderColor: '#c23531'
    // },
    series:[
        {
            type: 'tree',

            name: 'tree1',

            data: [data],

            top: '2%',
            left: '1%',
            bottom: '2%',
            right: '17%',
            symbolSize: 12,
            // edgeShape: "polyline",
            initialTreeDepth: -1,
            symbol: 'pin',

            label: {
                position: 'left',
                verticalAlign: 'middle',
                align: 'right',
                fontFamily: 'Times New Roman',
                fontSize: 16,
                fontStyle: 'oblique',
                // formatter: function (param) {
                //     if (param.name.match('Transposon')) {
                //         
                //     } else if (param.name.match('Transposon')) {
                //         color: '#1fadb0',
                //     } else if (param.name.match('Transposon')) {
                //         color: '#5c4db9',
                //     } else if (param.name.match('Transposon')) {
                //         color: '#e97c20',
                //     } else if (param.name.match('Transposon')) {
                        
                //     }
                // },
                rich: {
                    a: {
                        color: '#ff0000',
                        lineHeight: 20,
                        fontSize: 20,
                        fontFamily: 'Times New Roman',
                        fontStyle: 'oblique',
                    },
                    b: {
                        color: '#1fadb0',
                        lineHeight: 20,
                        fontSize: 20,
                        fontFamily: 'Times New Roman',
                        fontStyle: 'oblique',
                    },
                    c: {
                        color: '#5c4db9',
                        lineHeight: 20,
                        fontSize: 20,
                        fontFamily: 'Times New Roman',
                        fontStyle: 'oblique',
                    },
                    d: {
                        color: '#e97c20',
                        lineHeight: 20,
                        fontSize: 20,
                        fontFamily: 'Times New Roman',
                        fontStyle: 'oblique',
                    }
                },
            },
            itemStyle: {
                color: 'yellow',
                borderColor: 'green',
                borderWidth: '2',
                // borderType: 'solid',
            },
            lineStyle: {
                color: 'green',
            },

            leaves: {
                label: {
                    position: 'right',
                    verticalAlign: 'middle',
                    align: 'left'
                }
            },

            emphasis: {
                focus: 'descendant'
            },

            expandAndCollapse: true,

            animationDuration: 550,
            animationDurationUpdate: 750

        },
    ]
});

// option && myChart.setOption(option);
// myChart.on('click', function (params) {
//         var name = params.name;
//         if (name === "{a|Glucosinolate genes}") {
//             window.location.href="Glucosinolate_genes";
//         }
//         if (name === "{a|Auxin genes}") {
//             window.location.href="Auxin_genes";
//         }
//         if (name === "{a|Flowering genes}") {
//             window.location.href="Flowering_genes";
//         }
//         if (name === "{a|NBS genes}") {
//             window.location.href="NBS_genes";
//         }
//         if (name === "{a|PLK genes}") {
//             window.location.href="RLK_genes";
//         }
//         if (name === "{a|RLP genes}") {
//             window.location.href="RLP_genes";
//         }
//         if (name === "{a|Anthocyanin genes}") {
//             window.location.href="Anthocyanin_genes";
//         }
//         if (name === "{a|Transcription factors}") {
//             window.location.href="browse/TF.html";
//         }if (name === "{a|Transposable elements}") {
//             window.location.href="browse/TE.html";
//         }
//         if (name === "{a|MTA70}") {
//             window.location.href="MT-A70_genes";
//         }
//         if (name === "{a|WTAP}") {
//             window.location.href="Wtap_genes";
//         }
//         if (name === "{a|VIRILIZER}") {
//             window.location.href="VIR_N_genes";
//         }
//         if (name === "{a|HAKAI}") {
//             window.location.href="HAKAI_genes";
//         }
//         if (name === "{a|AlkB}") {
//             window.location.href="AlkB_genes";
//         }
//         if (name === "{a|YTH}") {
//             window.location.href="YTH_genes";
//         }
//         if (name === "{a|Annotations}") {
//             window.location.href="search/annotations.html";
//         }
//         if (name === "{a|CRISPR}") {
//             window.location.href="search/crispr.html";
//         }
//         if (name === "{a|Duplication type}") {
//             window.location.href="search/dulication.html";
//         }
//         if (name === "{a|Homologs}") {
//             window.location.href="search/homologs.html";
//         }
//         if (name === "{a|Synteny}") {
//             window.location.href="search/synteny.html";
//         }
//     });