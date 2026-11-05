

//        axisLabel:{
//           interval:0,//横轴信息全部显示
//           rotate:-30,//-15度角倾斜显示
//         },


var chartDom = document.getElementById('containers2');
var myChart = echarts.init(chartDom);
var option;

myChart.showLoading();

// var data = {
//     "name": "TBGR",
//     "children": [{"name": "","children": [{"name": "","children": [
//         {
//             "name": "",
//             "children": [{"name": "", "children": [{"name": "", "children": [{"name": "", "children": [{"name": "{a|Aar}",},]},]},]},]
//         },
//         {
//            "name": "",
//            "children": [
//             {"name": "100", "children": [{"name": "", "children": [
//                 {"name": "19", "children": [{"name": "", "children": [{"name": "", "children": [{"name": "", "children": [{"name": "", "children": [{"name": "", "children": [{"name": "", "children": [{"name": "", "children": [{"name": "", "children": [{"name": "{a|Aal}",},]},]},]},]},]},]},]},]},
//                     {"name": "", "children": [{"name": "22", "children": [{"name": "", "children": [{"name": "", "children": [{"name": "", "children": [{"name": "", "children": [{"name": "", "children": [{"name": "", "children": [{"name": "{a|Mer}",},]},]},]},]},]},]},
//                         {"name": "", "children": [{"name": "15", "children": [
//                             {"name": "", "children": [{"name": "30", "children": [{"name": "", "children": [{"name": "", "children": [{"name": "{a|Tar}",},]},]}, {"name": "", "children": [{"name": "", "children": [{"name": "{a|Esa}",},]},]},]},]},
//                             {"name": "", "children": [{"name": "22", "children": [{"name": "", "children": [{"name": "", "children": [{"name": "","children": [{"name": "","children": [{"name": "","children": [{"name": "","children": [{"name": "","children": [{"name": "","children": [{"name": "{a|Spa}",},]},]},]},]},]},]},]},]},
//                                 {"name": "", "children": [{"name": "18","children": [
//                                     {"name": "", "children": [{"name": "","children": [{"name": "","children": [{"name": "74","children": [
//                                             {"name": "", "children": [{"name": "56","children": [
//                                                     {"name": "", "children": [{"name": "24","children": [{"name": "", "children": [{"name": "","children": [{"name": "{a|Bni}",},]},]}, {"name": "", "children": [{"name": "","children": [{"name": "{a|Bju}",},]},]},]},]},
//                                                     {"name": "", "children": [{"name": "17","children": [{"name": "", "children": [{"name": "","children": [{"name": "{a|Bca}",},]},]},
//                                                             {"name": "", "children": [{"name": "26","children": [{"name": "", "children": [{"name": "","children": [{"name": "{a|Bra}",},]},]},
//                                                                     {"name": "", "children": [{"name": "32","children": [{"name": "","children": [{"name": "{a|Bna}",}, {"name": "", "children": [{"name": "","children": [{"name": "{a|Bol}",},]},]},]},]},]},]},]},]},]},]},]},
//                                             {"name": "", "children": [{"name": "", "children": [{"name": "","children": [{"name": "","children": [{"name": "","children": [{"name": "","children": [{"name": "","children": [{"name": "","children": [{"name": "{a|Rsa}",},]},]},]},]},]},]},]},]},]},]},]},]},
//                                     {"name": "", "children": [{"name": "28", "children": [
//                                                 {"name": "", "children": [{"name": "","children": [{"name": "","children": [{"name": "","children": [{"name": "","children": [{"name": "","children": [{"name": "","children": [{"name": "","children": [{"name": "","children": [{"name": "","children": [{"name": "{a|Sir}",},]},]},]},]},]},]},]},]},]},]},
//                                                 {"name": "", "children": [{"name": "","children": [{"name": "","children": [{"name": "","children": [{"name": "","children": [{"name": "","children": [{"name": "","children": [{"name": "{a|Iin}",},]},]},]},]},]},]},]},]},]},]},]},]},]},]},]},]},]},]},]},
//                  {"name": "", "children": [{"name": "30", "children": [
//                      {"name": "","children": [{"name": "","children": [{"name": "50","children": [
//                             {"name": "", "children": [{"name": "", "children": [{"name": "", "children": [{"name": "","children": [{"name": "","children": [{"name": "","children": [{"name": "","children": [{"name": "{a|Chi}",},]},]},]},]},]},]},]},
//                             {"name": "","children": [{"name": "","children": [{"name": "","children": [{"name": "32","children": [
//                                 {"name": "","children": [{"name": "","children": [{"name": "","children": [{"name": "","children": [{"name": "","children": [{"name": "","children": [{"name": "","children": [{"name": "","children": [{"name": "","children": [{"name": "","children": [{"name": "{a|Bvu}",},]},]},]},]},]},]},]},]},]},]},
//                                 {"name": "","children": [{"name": "","children": [{"name": "","children": [{"name": "","children": [{"name": "","children": [{"name": "","children": [{"name": "","children": [{"name": "","children": [{"name": "","children": [{"name": "","children": [{"name": "","children": [{"name": "","children": [{"name": "","children": [{"name": "{a|Lal}",},]},]},]},]},]},]},]},]},]},]},]},]},]},]},]},]},]},]},]},]},
//                      {"name": "","children": [{"name": "21", "children": [{"name": "", "children": [{"name": "", "children": [{"name": "", "children": [{"name": "","children": [{"name": "","children": [{"name": "","children": [{"name": "","children": [{"name": "","children": [{"name": "","children": [{"name": "{a|Lme}",},]},]},]},]},]},]},]},]},]},
//                             {"name": "","children": [{"name": "","children": [{"name": "53","children": [
//                                 {"name": "", "children": [{"name": "", "children": [{"name": "72","children": [{"name": "","children": [{"name": "","children": [{"name": "","children": [{"name": "{a|Ath}",},]},]},]},
//                                     {"name": "","children": [{"name": "76","children": [
//                                         {"name": "","children": [{"name": "","children": [{"name": "{a|Aha}",},]},]},
//                                         {"name": "","children": [{"name": "{a|Aly}",},]},]},]},]},]},]},
//                                 {"name": "","children": [{"name": "41","children": [
//                                     {"name": "","children": [{"name": "48","children": [{"name": "","children": [{"name": "","children": [{"name": "","children": [{"name": "{a|Csa}",},]},]},]},
//                                         {"name": "","children": [{"name": "","children": [{"name": "91","children": [
//                                             {"name": "","children": [{"name": "","children": [{"name": "{a|Cgr}",},]},]},
//                                             {"name": "","children": [{"name": "{a|Cru}",},]},]},]},]},]},]},
//                                     {"name": "","children": [{"name": "","children": [{"name": "","children": [{"name": "90","children": [
//                                         {"name": "","children": [{"name": "","children": [{"name": "{a|Bst}",},]},]},
//                                         {"name": "","children": [{"name": "","children": [{"name": "","children": [{"name": "{a|Bre}",},]},]},]},]},]},]},]},]},]},]},]},]},]},]}]},]},]},]}]},]},]
//     };

var data = {
    "name": "CGRPOEE",
    "children": [
        {
            "name": " ",
            "children": [
                {
                    "name": "Gammer",
                    "children": [
                        {"name": "{a|V1}"},
                        {"name": "{a|V2}"},
                        {"name": "{a|V3}"},
                    ]
                },
                {
                    "name": "T-Beta",
                    "children" : [
                        {
                            "name": "T-Aplha",
                            "children": [
                                {"name": "{a|T1}"},
                                {"name": "{a|T2}"},
                            ]
                        },
                        {
                            "name": "T-Aplha",
                            "children": [
                                {"name": "{a|T3}"},
                                {"name": "{a|T4}"},
                            ]
                        },
                    ]
                },
            ]
        },
        {
            "name": "R-WGD",
            "children": [
                {
                    "name": "  ",
                    "children": [
                        {
                            "name" : "P-WGD",
                            "children": [
                                {"name": "{a|P22}"},
                                {"name": "{a|P21}"},
                            ]
                        },
                        {
                            "name" : "  ",
                            "children": [
                                {"name": "{a|C2}"},
                                {"name": "{a|A2}"},
                            ]
                        },
                    ]
                },
                {
                    "name": "  ",
                    "children": [
                        {
                            "name" : "P-WGD",
                            "children": [
                                {"name": "{a|P12}"},
                                {"name": "{a|P11}"},
                            ]
                        },
                        {
                            "name" : "  ",
                            "children": [
                                {"name": "{a|C1}"},
                                {"name": "{a|A1}"},
                            ]
                        },
                    ]
                },
                
            ]
        },
        
    ]
};

myChart.hideLoading();
data.label={color: 'red',
			fontSize: '40'};
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
            left: '0%',
            bottom: '2%',
            right: '17%',
            symbolSize: 12,
            edgeShape: "polyline",
            initialTreeDepth: -1,
            symbol: 'none',

            label: {
                position: 'left',
                verticalAlign: 'middle',
                align: 'right',
                fontFamily: 'Times New Roman',
                fontSize: 16,
                // rotate:-5,
                // fontStyle: 'oblique',
             //    formatter: function (param) {
             //      if (param.name.match('Transposon')) {
             //         return '{a|' + param.name + '}'
             //     }
             // },
             rich: {
                a: {
                    color: 'red',
                    lineHeight: 20,
                    fontSize: 20,
                    fontFamily: 'Times New Roman',
                    // rotate:-10,
                    fontStyle: 'oblique',
                },
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
