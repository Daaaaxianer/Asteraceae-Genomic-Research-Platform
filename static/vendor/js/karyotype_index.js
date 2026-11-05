let jsTree = new JsTree($('#container'));
let data = [
    {
        "id": 9,
        "parentId": 0,
        "text": "Asteraceae"
    },
    {
        "id": 1,
        "parentId": 0,
        "text": "Asteraceae nodes",
        "child": [
            {
                "id": 2,
                "parentId": 1,
                "text": "<div class=\"row\">\n" +
                    "    <div class=\"col-lg-10\">\n" +
                    "        <p style=\"margin-bottom: 5px\">AAK-I\n</p>\n" +
                    "    </div>\n" +
                    "    <div class=\"col-lg-2\" style=\"padding: 0\">\n" +
                    "        <a href=\"karyotype/AAK-I\" target=\"_blank\" class=\"bi bi-caret-right\"></a>\n" +
                    "        <a href=\"../../static/image/karyoty/AAK-I.png\" target=\"_blank\"  class=\"bi bi-eye\"></a>\n" +
                    "    </div>\n" +
                    "</div>",
            },
            {
                "id": 2,
                "parentId": 1,
                "text": "<div class=\"row\">\n" +
                    "    <div class=\"col-lg-10\">\n" +
                    "        <p style=\"margin-bottom: 5px\">AAK-II\n</p>\n" +
                    "    </div>\n" +
                    "    <div class=\"col-lg-2\" style=\"padding: 0\">\n" +
                    "        <a href=\"karyotype/AAK-II\" target=\"_blank\" class=\"bi bi-caret-right\"></a>\n" +
                    "        <a href=\"../../static/image/karyoty/AAK-II.png\" target=\"_blank\"  class=\"bi bi-eye\"></a>\n" +
                    "    </div>\n" +
                    "</div>",
            },
            {
                "id": 2,
                "parentId": 1,
                "text": "<div class=\"row\">\n" +
                    "    <div class=\"col-lg-10\">\n" +
                    "        <p style=\"margin-bottom: 5px\">ACAK\n</p>\n" +
                    "    </div>\n" +
                    "    <div class=\"col-lg-2\" style=\"padding: 0\">\n" +
                    "        <a href=\"karyotype/ACAK\" target=\"_blank\" class=\"bi bi-caret-right\"></a>\n" +
                    "        <a href=\"../../static/image/karyoty/ACAK.png\" target=\"_blank\"  class=\"bi bi-eye\"></a>\n" +
                    "    </div>\n" +
                    "</div>",
            },
            {
                "id": 2,
                "parentId": 1,
                "text": "<div class=\"row\">\n" +
                    "    <div class=\"col-lg-10\">\n" +
                    "        <p style=\"margin-bottom: 5px\">ASAK-I\n</p>\n" +
                    "    </div>\n" +
                    "    <div class=\"col-lg-2\" style=\"padding: 0\">\n" +
                    "        <a href=\"karyotype/ASAK-I\" target=\"_blank\" class=\"bi bi-caret-right\"></a>\n" +
                    "        <a href=\"../../static/image/karyoty/ASAK-I.png\" target=\"_blank\"  class=\"bi bi-eye\"></a>\n" +
                    "    </div>\n" +
                    "</div>",
            },
            {
                "id": 2,
                "parentId": 1,
                "text": "<div class=\"row\">\n" +
                    "    <div class=\"col-lg-10\">\n" +
                    "        <p style=\"margin-bottom: 5px\">ASAK-II\n</p>\n" +
                    "    </div>\n" +
                    "    <div class=\"col-lg-2\" style=\"padding: 0\">\n" +
                    "        <a href=\"karyotype/ASAK-II\" target=\"_blank\" class=\"bi bi-caret-right\"></a>\n" +
                    "        <a href=\"../../static/image/karyoty/ASAK-II.png\" target=\"_blank\"  class=\"bi bi-eye\"></a>\n" +
                    "    </div>\n" +
                    "</div>",
            },
            {
                "id": 2,
                "parentId": 1,
                "text": "<div class=\"row\">\n" +
                    "    <div class=\"col-lg-10\">\n" +
                    "        <p style=\"margin-bottom: 5px\">ASAK-III\n</p>\n" +
                    "    </div>\n" +
                    "    <div class=\"col-lg-2\" style=\"padding: 0\">\n" +
                    "        <a href=\"karyotype/ASAK-III\" target=\"_blank\" class=\"bi bi-caret-right\"></a>\n" +
                    "        <a href=\"../../static/image/karyoty/ASAK-III.png\" target=\"_blank\"  class=\"bi bi-eye\"></a>\n" +
                    "    </div>\n" +
                    "</div>",
            },
            {
                "id": 2,
                "parentId": 1,
                "text": "<div class=\"row\">\n" +
                    "    <div class=\"col-lg-10\">\n" +
                    "        <p style=\"margin-bottom: 5px\">ASAK-IV\n</p>\n" +
                    "    </div>\n" +
                    "    <div class=\"col-lg-2\" style=\"padding: 0\">\n" +
                    "        <a href=\"karyotype/ASAK-IV\" target=\"_blank\" class=\"bi bi-caret-right\"></a>\n" +
                    "        <a href=\"../../static/image/karyoty/ASAK-IV.png\" target=\"_blank\"  class=\"bi bi-eye\"></a>\n" +
                    "    </div>\n" +
                    "</div>",
            },
            {
                "id": 2,
                "parentId": 1,
                "text": "<div class=\"row\">\n" +
                    "    <div class=\"col-lg-10\">\n" +
                    "        <p style=\"margin-bottom: 5px\">ASAK-IX\n</p>\n" +
                    "    </div>\n" +
                    "    <div class=\"col-lg-2\" style=\"padding: 0\">\n" +
                    "        <a href=\"karyotype/ASAK-IX\" target=\"_blank\" class=\"bi bi-caret-right\"></a>\n" +
                    "        <a href=\"../../static/image/karyoty/ASAK-IX.png\" target=\"_blank\"  class=\"bi bi-eye\"></a>\n" +
                    "    </div>\n" +
                    "</div>",
            },
            {
                "id": 2,
                "parentId": 1,
                "text": "<div class=\"row\">\n" +
                    "    <div class=\"col-lg-10\">\n" +
                    "        <p style=\"margin-bottom: 5px\">ASAK-V\n</p>\n" +
                    "    </div>\n" +
                    "    <div class=\"col-lg-2\" style=\"padding: 0\">\n" +
                    "        <a href=\"karyotype/ASAK-V\" target=\"_blank\" class=\"bi bi-caret-right\"></a>\n" +
                    "        <a href=\"../../static/image/karyoty/ASAK-V.png\" target=\"_blank\"  class=\"bi bi-eye\"></a>\n" +
                    "    </div>\n" +
                    "</div>",
            },
            {
                "id": 2,
                "parentId": 1,
                "text": "<div class=\"row\">\n" +
                    "    <div class=\"col-lg-10\">\n" +
                    "        <p style=\"margin-bottom: 5px\">ASAK-VI\n</p>\n" +
                    "    </div>\n" +
                    "    <div class=\"col-lg-2\" style=\"padding: 0\">\n" +
                    "        <a href=\"karyotype/ASAK-VI\" target=\"_blank\" class=\"bi bi-caret-right\"></a>\n" +
                    "        <a href=\"../../static/image/karyoty/ASAK-VI.png\" target=\"_blank\"  class=\"bi bi-eye\"></a>\n" +
                    "    </div>\n" +
                    "</div>",
            },
            {
                "id": 2,
                "parentId": 1,
                "text": "<div class=\"row\">\n" +
                    "    <div class=\"col-lg-10\">\n" +
                    "        <p style=\"margin-bottom: 5px\">ASAK-VII\n</p>\n" +
                    "    </div>\n" +
                    "    <div class=\"col-lg-2\" style=\"padding: 0\">\n" +
                    "        <a href=\"karyotype/ASAK-VII\" target=\"_blank\" class=\"bi bi-caret-right\"></a>\n" +
                    "        <a href=\"../../static/image/karyoty/ASAK-VII.png\" target=\"_blank\"  class=\"bi bi-eye\"></a>\n" +
                    "    </div>\n" +
                    "</div>",
            },
            {
                "id": 2,
                "parentId": 1,
                "text": "<div class=\"row\">\n" +
                    "    <div class=\"col-lg-10\">\n" +
                    "        <p style=\"margin-bottom: 5px\">ASAK-VIII\n</p>\n" +
                    "    </div>\n" +
                    "    <div class=\"col-lg-2\" style=\"padding: 0\">\n" +
                    "        <a href=\"karyotype/ASAK-VIII\" target=\"_blank\" class=\"bi bi-caret-right\"></a>\n" +
                    "        <a href=\"../../static/image/karyoty/ASAK-VIII.png\" target=\"_blank\"  class=\"bi bi-eye\"></a>\n" +
                    "    </div>\n" +
                    "</div>",
            },
            {
                "id": 2,
                "parentId": 1,
                "text": "<div class=\"row\">\n" +
                    "    <div class=\"col-lg-10\">\n" +
                    "        <p style=\"margin-bottom: 5px\">ASAK-X\n</p>\n" +
                    "    </div>\n" +
                    "    <div class=\"col-lg-2\" style=\"padding: 0\">\n" +
                    "        <a href=\"karyotype/ASAK-X\" target=\"_blank\" class=\"bi bi-caret-right\"></a>\n" +
                    "        <a href=\"../../static/image/karyoty/ASAK-X.png\" target=\"_blank\"  class=\"bi bi-eye\"></a>\n" +
                    "    </div>\n" +
                    "</div>",
            },
            {
                "id": 2,
                "parentId": 1,
                "text": "<div class=\"row\">\n" +
                    "    <div class=\"col-lg-10\">\n" +
                    "        <p style=\"margin-bottom: 5px\">ASAK-XI\n</p>\n" +
                    "    </div>\n" +
                    "    <div class=\"col-lg-2\" style=\"padding: 0\">\n" +
                    "        <a href=\"karyotype/ASAK-XI\" target=\"_blank\" class=\"bi bi-caret-right\"></a>\n" +
                    "        <a href=\"../../static/image/karyoty/ASAK-XI.png\" target=\"_blank\"  class=\"bi bi-eye\"></a>\n" +
                    "    </div>\n" +
                    "</div>",
            },
            {
                "id": 2,
                "parentId": 1,
                "text": "<div class=\"row\">\n" +
                    "    <div class=\"col-lg-10\">\n" +
                    "        <p style=\"margin-bottom: 5px\">ASAK-XII\n</p>\n" +
                    "    </div>\n" +
                    "    <div class=\"col-lg-2\" style=\"padding: 0\">\n" +
                    "        <a href=\"karyotype/ASAK-XII\" target=\"_blank\" class=\"bi bi-caret-right\"></a>\n" +
                    "        <a href=\"../../static/image/karyoty/ASAK-XII.png\" target=\"_blank\"  class=\"bi bi-eye\"></a>\n" +
                    "    </div>\n" +
                    "</div>",
            },
            {
                "id": 2,
                "parentId": 1,
                "text": "<div class=\"row\">\n" +
                    "    <div class=\"col-lg-10\">\n" +
                    "        <p style=\"margin-bottom: 5px\">ASAK-XIII\n</p>\n" +
                    "    </div>\n" +
                    "    <div class=\"col-lg-2\" style=\"padding: 0\">\n" +
                    "        <a href=\"karyotype/ASAK-XIII\" target=\"_blank\" class=\"bi bi-caret-right\"></a>\n" +
                    "        <a href=\"../../static/image/karyoty/ASAK-XIII.png\" target=\"_blank\"  class=\"bi bi-eye\"></a>\n" +
                    "    </div>\n" +
                    "</div>",
            },
            {
                "id": 2,
                "parentId": 1,
                "text": "<div class=\"row\">\n" +
                    "    <div class=\"col-lg-10\">\n" +
                    "        <p style=\"margin-bottom: 5px\">ASAK-XIV\n</p>\n" +
                    "    </div>\n" +
                    "    <div class=\"col-lg-2\" style=\"padding: 0\">\n" +
                    "        <a href=\"karyotype/ASAK-XIV\" target=\"_blank\" class=\"bi bi-caret-right\"></a>\n" +
                    "        <a href=\"../../static/image/karyoty/ASAK-XIV.png\" target=\"_blank\"  class=\"bi bi-eye\"></a>\n" +
                    "    </div>\n" +
                    "</div>",
            },
            {
                "id": 2,
                "parentId": 1,
                "text": "<div class=\"row\">\n" +
                    "    <div class=\"col-lg-10\">\n" +
                    "        <p style=\"margin-bottom: 5px\">ASAK-XIX\n</p>\n" +
                    "    </div>\n" +
                    "    <div class=\"col-lg-2\" style=\"padding: 0\">\n" +
                    "        <a href=\"karyotype/ASAK-XIX\" target=\"_blank\" class=\"bi bi-caret-right\"></a>\n" +
                    "        <a href=\"../../static/image/karyoty/ASAK-XIX.png\" target=\"_blank\"  class=\"bi bi-eye\"></a>\n" +
                    "    </div>\n" +
                    "</div>",
            },
            {
                "id": 2,
                "parentId": 1,
                "text": "<div class=\"row\">\n" +
                    "    <div class=\"col-lg-10\">\n" +
                    "        <p style=\"margin-bottom: 5px\">ASAK-XV\n</p>\n" +
                    "    </div>\n" +
                    "    <div class=\"col-lg-2\" style=\"padding: 0\">\n" +
                    "        <a href=\"karyotype/ASAK-XV\" target=\"_blank\" class=\"bi bi-caret-right\"></a>\n" +
                    "        <a href=\"../../static/image/karyoty/ASAK-XV.png\" target=\"_blank\"  class=\"bi bi-eye\"></a>\n" +
                    "    </div>\n" +
                    "</div>",
            },
            {
                "id": 2,
                "parentId": 1,
                "text": "<div class=\"row\">\n" +
                    "    <div class=\"col-lg-10\">\n" +
                    "        <p style=\"margin-bottom: 5px\">ASAK-XVI\n</p>\n" +
                    "    </div>\n" +
                    "    <div class=\"col-lg-2\" style=\"padding: 0\">\n" +
                    "        <a href=\"karyotype/ASAK-XVI\" target=\"_blank\" class=\"bi bi-caret-right\"></a>\n" +
                    "        <a href=\"../../static/image/karyoty/ASAK-XVI.png\" target=\"_blank\"  class=\"bi bi-eye\"></a>\n" +
                    "    </div>\n" +
                    "</div>",
            },
            {
                "id": 2,
                "parentId": 1,
                "text": "<div class=\"row\">\n" +
                    "    <div class=\"col-lg-10\">\n" +
                    "        <p style=\"margin-bottom: 5px\">ASAK-XVII\n</p>\n" +
                    "    </div>\n" +
                    "    <div class=\"col-lg-2\" style=\"padding: 0\">\n" +
                    "        <a href=\"karyotype/ASAK-XVII\" target=\"_blank\" class=\"bi bi-caret-right\"></a>\n" +
                    "        <a href=\"../../static/image/karyoty/ASAK-XVII.png\" target=\"_blank\"  class=\"bi bi-eye\"></a>\n" +
                    "    </div>\n" +
                    "</div>",
            },
            {
                "id": 2,
                "parentId": 1,
                "text": "<div class=\"row\">\n" +
                    "    <div class=\"col-lg-10\">\n" +
                    "        <p style=\"margin-bottom: 5px\">ASAK-XVIII\n</p>\n" +
                    "    </div>\n" +
                    "    <div class=\"col-lg-2\" style=\"padding: 0\">\n" +
                    "        <a href=\"karyotype/ASAK-XVIII\" target=\"_blank\" class=\"bi bi-caret-right\"></a>\n" +
                    "        <a href=\"../../static/image/karyoty/ASAK-XVIII.png\" target=\"_blank\"  class=\"bi bi-eye\"></a>\n" +
                    "    </div>\n" +
                    "</div>",
            },
            {
                "id": 2,
                "parentId": 1,
                "text": "<div class=\"row\">\n" +
                    "    <div class=\"col-lg-10\">\n" +
                    "        <p style=\"margin-bottom: 5px\">CAAK-I\n</p>\n" +
                    "    </div>\n" +
                    "    <div class=\"col-lg-2\" style=\"padding: 0\">\n" +
                    "        <a href=\"karyotype/CAAK-I\" target=\"_blank\" class=\"bi bi-caret-right\"></a>\n" +
                    "        <a href=\"../../static/image/karyoty/CAAK-I.png\" target=\"_blank\"  class=\"bi bi-eye\"></a>\n" +
                    "    </div>\n" +
                    "</div>",
            },
            {
                "id": 2,
                "parentId": 1,
                "text": "<div class=\"row\">\n" +
                    "    <div class=\"col-lg-10\">\n" +
                    "        <p style=\"margin-bottom: 5px\">CAAK-II\n</p>\n" +
                    "    </div>\n" +
                    "    <div class=\"col-lg-2\" style=\"padding: 0\">\n" +
                    "        <a href=\"karyotype/CAAK-II\" target=\"_blank\" class=\"bi bi-caret-right\"></a>\n" +
                    "        <a href=\"../../static/image/karyoty/CAAK-II.png\" target=\"_blank\"  class=\"bi bi-eye\"></a>\n" +
                    "    </div>\n" +
                    "</div>",
            },
            {
                "id": 2,
                "parentId": 1,
                "text": "<div class=\"row\">\n" +
                    "    <div class=\"col-lg-10\">\n" +
                    "        <p style=\"margin-bottom: 5px\">CAAK-III\n</p>\n" +
                    "    </div>\n" +
                    "    <div class=\"col-lg-2\" style=\"padding: 0\">\n" +
                    "        <a href=\"karyotype/CAAK-III\" target=\"_blank\" class=\"bi bi-caret-right\"></a>\n" +
                    "        <a href=\"../../static/image/karyoty/CAAK-III.png\" target=\"_blank\"  class=\"bi bi-eye\"></a>\n" +
                    "    </div>\n" +
                    "</div>",
            },
            {
                "id": 2,
                "parentId": 1,
                "text": "<div class=\"row\">\n" +
                    "    <div class=\"col-lg-10\">\n" +
                    "        <p style=\"margin-bottom: 5px\">CAAK-IV\n</p>\n" +
                    "    </div>\n" +
                    "    <div class=\"col-lg-2\" style=\"padding: 0\">\n" +
                    "        <a href=\"karyotype/CAAK-IV\" target=\"_blank\" class=\"bi bi-caret-right\"></a>\n" +
                    "        <a href=\"../../static/image/karyoty/CAAK-IV.png\" target=\"_blank\"  class=\"bi bi-eye\"></a>\n" +
                    "    </div>\n" +
                    "</div>",
            },
            {
                "id": 2,
                "parentId": 1,
                "text": "<div class=\"row\">\n" +
                    "    <div class=\"col-lg-10\">\n" +
                    "        <p style=\"margin-bottom: 5px\">CIAK-I\n</p>\n" +
                    "    </div>\n" +
                    "    <div class=\"col-lg-2\" style=\"padding: 0\">\n" +
                    "        <a href=\"karyotype/CIAK-I\" target=\"_blank\" class=\"bi bi-caret-right\"></a>\n" +
                    "        <a href=\"../../static/image/karyoty/CIAK-I.png\" target=\"_blank\"  class=\"bi bi-eye\"></a>\n" +
                    "    </div>\n" +
                    "</div>",
            },
            {
                "id": 2,
                "parentId": 1,
                "text": "<div class=\"row\">\n" +
                    "    <div class=\"col-lg-10\">\n" +
                    "        <p style=\"margin-bottom: 5px\">CIAK-II\n</p>\n" +
                    "    </div>\n" +
                    "    <div class=\"col-lg-2\" style=\"padding: 0\">\n" +
                    "        <a href=\"karyotype/CIAK-II\" target=\"_blank\" class=\"bi bi-caret-right\"></a>\n" +
                    "        <a href=\"../../static/image/karyoty/CIAK-II.png\" target=\"_blank\"  class=\"bi bi-eye\"></a>\n" +
                    "    </div>\n" +
                    "</div>",
            }
        ]
    },
    // ----------------------------------------分界线--------------------------------------------
    {
        "id": 6,
        "parentId": 0,
        "text": "Asteraceae species",
        "child": [
            {
                "id": 2,
                "parentId": 1,
                "text": "<div class=\"row\">\n" +
                    "    <div class=\"col-lg-10\">\n" +
                    "        <p style=\"margin-bottom: 5px\">Ambrosia trifida\n</p>\n" +
                    "    </div>\n" +
                    "    <div class=\"col-lg-2\" style=\"padding: 0\">\n" +
                    "        <a href=\"karyotype/Ambrosia_trifida\" target=\"_blank\" class=\"bi bi-caret-right\"></a>\n" +
                    "        <a href=\"../../static/image/karyoty/Ambrosia_trifida.png\" target=\"_blank\"  class=\"bi bi-eye\"></a>\n" +
                    "    </div>\n" +
                    "</div>",
            },
            {
                "id": 2,
                "parentId": 1,
                "text": "<div class=\"row\">\n" +
                    "    <div class=\"col-lg-10\">\n" +
                    "        <p style=\"margin-bottom: 5px\">Arctium lappa\n</p>\n" +
                    "    </div>\n" +
                    "    <div class=\"col-lg-2\" style=\"padding: 0\">\n" +
                    "        <a href=\"karyotype/Arctium_lappa\" target=\"_blank\" class=\"bi bi-caret-right\"></a>\n" +
                    "        <a href=\"../../static/image/karyoty/Arctium_lappa.png\" target=\"_blank\"  class=\"bi bi-eye\"></a>\n" +
                    "    </div>\n" +
                    "</div>",
            },
            {
                "id": 2,
                "parentId": 1,
                "text": "<div class=\"row\">\n" +
                    "    <div class=\"col-lg-10\">\n" +
                    "        <p style=\"margin-bottom: 5px\">Carthamus tinctorius\n</p>\n" +
                    "    </div>\n" +
                    "    <div class=\"col-lg-2\" style=\"padding: 0\">\n" +
                    "        <a href=\"karyotype/Carthamus_tinctorius\" target=\"_blank\" class=\"bi bi-caret-right\"></a>\n" +
                    "        <a href=\"../../static/image/karyoty/Carthamus_tinctorius.png\" target=\"_blank\"  class=\"bi bi-eye\"></a>\n" +
                    "    </div>\n" +
                    "</div>",
            },
            {
                "id": 2,
                "parentId": 1,
                "text": "<div class=\"row\">\n" +
                    "    <div class=\"col-lg-10\">\n" +
                    "        <p style=\"margin-bottom: 5px\">Centaurea solstitialis\n</p>\n" +
                    "    </div>\n" +
                    "    <div class=\"col-lg-2\" style=\"padding: 0\">\n" +
                    "        <a href=\"karyotype/Centaurea_solstitialis\" target=\"_blank\" class=\"bi bi-caret-right\"></a>\n" +
                    "        <a href=\"../../static/image/karyoty/Centaurea_solstitialis.png\" target=\"_blank\"  class=\"bi bi-eye\"></a>\n" +
                    "    </div>\n" +
                    "</div>",
            },
            {
                "id": 2,
                "parentId": 1,
                "text": "<div class=\"row\">\n" +
                    "    <div class=\"col-lg-10\">\n" +
                    "        <p style=\"margin-bottom: 5px\">Chrysanthemum lavandulifolium\n</p>\n" +
                    "    </div>\n" +
                    "    <div class=\"col-lg-2\" style=\"padding: 0\">\n" +
                    "        <a href=\"karyotype/Chrysanthemum_lavandulifolium\" target=\"_blank\" class=\"bi bi-caret-right\"></a>\n" +
                    "        <a href=\"../../static/image/karyoty/Chrysanthemum_lavandulifolium.png\" target=\"_blank\"  class=\"bi bi-eye\"></a>\n" +
                    "    </div>\n" +
                    "</div>",
            },
            {
                "id": 2,
                "parentId": 1,
                "text": "<div class=\"row\">\n" +
                    "    <div class=\"col-lg-10\">\n" +
                    "        <p style=\"margin-bottom: 5px\">Cichorium intybus\n</p>\n" +
                    "    </div>\n" +
                    "    <div class=\"col-lg-2\" style=\"padding: 0\">\n" +
                    "        <a href=\"karyotype/Cichorium_intybus\" target=\"_blank\" class=\"bi bi-caret-right\"></a>\n" +
                    "        <a href=\"../../static/image/karyoty/Cichorium_intybus.png\" target=\"_blank\"  class=\"bi bi-eye\"></a>\n" +
                    "    </div>\n" +
                    "</div>",
            },
            {
                "id": 2,
                "parentId": 1,
                "text": "<div class=\"row\">\n" +
                    "    <div class=\"col-lg-10\">\n" +
                    "        <p style=\"margin-bottom: 5px\">Cosmos bipinnatus\n</p>\n" +
                    "    </div>\n" +
                    "    <div class=\"col-lg-2\" style=\"padding: 0\">\n" +
                    "        <a href=\"karyotype/Cosmos_bipinnatus\" target=\"_blank\" class=\"bi bi-caret-right\"></a>\n" +
                    "        <a href=\"../../static/image/karyoty/Cosmos_bipinnatus.png\" target=\"_blank\"  class=\"bi bi-eye\"></a>\n" +
                    "    </div>\n" +
                    "</div>",
            },
            {
                "id": 2,
                "parentId": 1,
                "text": "<div class=\"row\">\n" +
                    "    <div class=\"col-lg-10\">\n" +
                    "        <p style=\"margin-bottom: 5px\">Cynara cardunculus\n</p>\n" +
                    "    </div>\n" +
                    "    <div class=\"col-lg-2\" style=\"padding: 0\">\n" +
                    "        <a href=\"karyotype/Cynara_cardunculus\" target=\"_blank\" class=\"bi bi-caret-right\"></a>\n" +
                    "        <a href=\"../../static/image/karyoty/Cynara_cardunculus.png\" target=\"_blank\"  class=\"bi bi-eye\"></a>\n" +
                    "    </div>\n" +
                    "</div>",
            },
            {
                "id": 2,
                "parentId": 1,
                "text": "<div class=\"row\">\n" +
                    "    <div class=\"col-lg-10\">\n" +
                    "        <p style=\"margin-bottom: 5px\">Dahlia pinnata\n</p>\n" +
                    "    </div>\n" +
                    "    <div class=\"col-lg-2\" style=\"padding: 0\">\n" +
                    "        <a href=\"karyotype/Dahlia_pinnata\" target=\"_blank\" class=\"bi bi-caret-right\"></a>\n" +
                    "        <a href=\"../../static/image/karyoty/Dahlia_pinnata.png\" target=\"_blank\"  class=\"bi bi-eye\"></a>\n" +
                    "    </div>\n" +
                    "</div>",
            },
            {
                "id": 2,
                "parentId": 1,
                "text": "<div class=\"row\">\n" +
                    "    <div class=\"col-lg-10\">\n" +
                    "        <p style=\"margin-bottom: 5px\">Deinandra increscens\n</p>\n" +
                    "    </div>\n" +
                    "    <div class=\"col-lg-2\" style=\"padding: 0\">\n" +
                    "        <a href=\"karyotype/Deinandra_increscens\" target=\"_blank\" class=\"bi bi-caret-right\"></a>\n" +
                    "        <a href=\"../../static/image/karyoty/Deinandra_increscens.png\" target=\"_blank\"  class=\"bi bi-eye\"></a>\n" +
                    "    </div>\n" +
                    "</div>",
            },
            {
                "id": 2,
                "parentId": 1,
                "text": "<div class=\"row\">\n" +
                    "    <div class=\"col-lg-10\">\n" +
                    "        <p style=\"margin-bottom: 5px\">Erigeron canadensis\n</p>\n" +
                    "    </div>\n" +
                    "    <div class=\"col-lg-2\" style=\"padding: 0\">\n" +
                    "        <a href=\"karyotype/Erigeron_canadensis\" target=\"_blank\" class=\"bi bi-caret-right\"></a>\n" +
                    "        <a href=\"../../static/image/karyoty/Erigeron_canadensis.png\" target=\"_blank\"  class=\"bi bi-eye\"></a>\n" +
                    "    </div>\n" +
                    "</div>",
            },
            {
                "id": 2,
                "parentId": 1,
                "text": "<div class=\"row\">\n" +
                    "    <div class=\"col-lg-10\">\n" +
                    "        <p style=\"margin-bottom: 5px\">Flaveria linearis\n</p>\n" +
                    "    </div>\n" +
                    "    <div class=\"col-lg-2\" style=\"padding: 0\">\n" +
                    "        <a href=\"karyotype/Flaveria_linearis\" target=\"_blank\" class=\"bi bi-caret-right\"></a>\n" +
                    "        <a href=\"../../static/image/karyoty/Flaveria_linearis.png\" target=\"_blank\"  class=\"bi bi-eye\"></a>\n" +
                    "    </div>\n" +
                    "</div>",
            },
            {
                "id": 2,
                "parentId": 1,
                "text": "<div class=\"row\">\n" +
                    "    <div class=\"col-lg-10\">\n" +
                    "        <p style=\"margin-bottom: 5px\">Glebionis coronaria\n</p>\n" +
                    "    </div>\n" +
                    "    <div class=\"col-lg-2\" style=\"padding: 0\">\n" +
                    "        <a href=\"karyotype/Glebionis_coronaria\" target=\"_blank\" class=\"bi bi-caret-right\"></a>\n" +
                    "        <a href=\"../../static/image/karyoty/Glebionis_coronaria.png\" target=\"_blank\"  class=\"bi bi-eye\"></a>\n" +
                    "    </div>\n" +
                    "</div>",
            },
            {
                "id": 2,
                "parentId": 1,
                "text": "<div class=\"row\">\n" +
                    "    <div class=\"col-lg-10\">\n" +
                    "        <p style=\"margin-bottom: 5px\">Helianthus annuus\n</p>\n" +
                    "    </div>\n" +
                    "    <div class=\"col-lg-2\" style=\"padding: 0\">\n" +
                    "        <a href=\"karyotype/Helianthus_annuus\" target=\"_blank\" class=\"bi bi-caret-right\"></a>\n" +
                    "        <a href=\"../../static/image/karyoty/Helianthus_annuus.png\" target=\"_blank\"  class=\"bi bi-eye\"></a>\n" +
                    "    </div>\n" +
                    "</div>",
            },
            {
                "id": 2,
                "parentId": 1,
                "text": "<div class=\"row\">\n" +
                    "    <div class=\"col-lg-10\">\n" +
                    "        <p style=\"margin-bottom: 5px\">Lactuca sativa\n</p>\n" +
                    "    </div>\n" +
                    "    <div class=\"col-lg-2\" style=\"padding: 0\">\n" +
                    "        <a href=\"karyotype/Lactuca_sativa\" target=\"_blank\" class=\"bi bi-caret-right\"></a>\n" +
                    "        <a href=\"../../static/image/karyoty/Lactuca_sativa.png\" target=\"_blank\"  class=\"bi bi-eye\"></a>\n" +
                    "    </div>\n" +
                    "</div>",
            },
            {
                "id": 2,
                "parentId": 1,
                "text": "<div class=\"row\">\n" +
                    "    <div class=\"col-lg-10\">\n" +
                    "        <p style=\"margin-bottom: 5px\">Logfia minima\n</p>\n" +
                    "    </div>\n" +
                    "    <div class=\"col-lg-2\" style=\"padding: 0\">\n" +
                    "        <a href=\"karyotype/Logfia_minima\" target=\"_blank\" class=\"bi bi-caret-right\"></a>\n" +
                    "        <a href=\"../../static/image/karyoty/Logfia_minima.png\" target=\"_blank\"  class=\"bi bi-eye\"></a>\n" +
                    "    </div>\n" +
                    "</div>",
            },
            {
                "id": 2,
                "parentId": 1,
                "text": "<div class=\"row\">\n" +
                    "    <div class=\"col-lg-10\">\n" +
                    "        <p style=\"margin-bottom: 5px\">Mikania micrantha\n</p>\n" +
                    "    </div>\n" +
                    "    <div class=\"col-lg-2\" style=\"padding: 0\">\n" +
                    "        <a href=\"karyotype/Mikania_micrantha\" target=\"_blank\" class=\"bi bi-caret-right\"></a>\n" +
                    "        <a href=\"../../static/image/karyoty/Mikania_micrantha.png\" target=\"_blank\"  class=\"bi bi-eye\"></a>\n" +
                    "    </div>\n" +
                    "</div>",
            },
            {
                "id": 2,
                "parentId": 1,
                "text": "<div class=\"row\">\n" +
                    "    <div class=\"col-lg-10\">\n" +
                    "        <p style=\"margin-bottom: 5px\">Pseudognaphalium luteoalbum\n</p>\n" +
                    "    </div>\n" +
                    "    <div class=\"col-lg-2\" style=\"padding: 0\">\n" +
                    "        <a href=\"karyotype/Pseudognaphalium_luteoalbum\" target=\"_blank\" class=\"bi bi-caret-right\"></a>\n" +
                    "        <a href=\"../../static/image/karyoty/Pseudognaphalium_luteoalbum.png\" target=\"_blank\"  class=\"bi bi-eye\"></a>\n" +
                    "    </div>\n" +
                    "</div>",
            },
            {
                "id": 2,
                "parentId": 1,
                "text": "<div class=\"row\">\n" +
                    "    <div class=\"col-lg-10\">\n" +
                    "        <p style=\"margin-bottom: 5px\">Pulicaria dysenterica\n</p>\n" +
                    "    </div>\n" +
                    "    <div class=\"col-lg-2\" style=\"padding: 0\">\n" +
                    "        <a href=\"karyotype/Pulicaria_dysenterica\" target=\"_blank\" class=\"bi bi-caret-right\"></a>\n" +
                    "        <a href=\"../../static/image/karyoty/Pulicaria_dysenterica.png\" target=\"_blank\"  class=\"bi bi-eye\"></a>\n" +
                    "    </div>\n" +
                    "</div>",
            },
            {
                "id": 2,
                "parentId": 1,
                "text": "<div class=\"row\">\n" +
                    "    <div class=\"col-lg-10\">\n" +
                    "        <p style=\"margin-bottom: 5px\">Saussurea involucrata\n</p>\n" +
                    "    </div>\n" +
                    "    <div class=\"col-lg-2\" style=\"padding: 0\">\n" +
                    "        <a href=\"karyotype/Saussurea_involucrata\" target=\"_blank\" class=\"bi bi-caret-right\"></a>\n" +
                    "        <a href=\"../../static/image/karyoty/Saussurea_involucrata.png\" target=\"_blank\"  class=\"bi bi-eye\"></a>\n" +
                    "    </div>\n" +
                    "</div>",
            },
            {
                "id": 2,
                "parentId": 1,
                "text": "<div class=\"row\">\n" +
                    "    <div class=\"col-lg-10\">\n" +
                    "        <p style=\"margin-bottom: 5px\">Senecio squalidus\n</p>\n" +
                    "    </div>\n" +
                    "    <div class=\"col-lg-2\" style=\"padding: 0\">\n" +
                    "        <a href=\"karyotype/Senecio_squalidus\" target=\"_blank\" class=\"bi bi-caret-right\"></a>\n" +
                    "        <a href=\"../../static/image/karyoty/Senecio_squalidus.png\" target=\"_blank\"  class=\"bi bi-eye\"></a>\n" +
                    "    </div>\n" +
                    "</div>",
            },
            {
                "id": 2,
                "parentId": 1,
                "text": "<div class=\"row\">\n" +
                    "    <div class=\"col-lg-10\">\n" +
                    "        <p style=\"margin-bottom: 5px\">Smallanthus sonchifolius\n</p>\n" +
                    "    </div>\n" +
                    "    <div class=\"col-lg-2\" style=\"padding: 0\">\n" +
                    "        <a href=\"karyotype/Smallanthus_sonchifolius\" target=\"_blank\" class=\"bi bi-caret-right\"></a>\n" +
                    "        <a href=\"../../static/image/karyoty/Smallanthus_sonchifolius.png\" target=\"_blank\"  class=\"bi bi-eye\"></a>\n" +
                    "    </div>\n" +
                    "</div>",
            },
            {
                "id": 2,
                "parentId": 1,
                "text": "<div class=\"row\">\n" +
                    "    <div class=\"col-lg-10\">\n" +
                    "        <p style=\"margin-bottom: 5px\">Solidago caesia\n</p>\n" +
                    "    </div>\n" +
                    "    <div class=\"col-lg-2\" style=\"padding: 0\">\n" +
                    "        <a href=\"karyotype/Solidago_caesia\" target=\"_blank\" class=\"bi bi-caret-right\"></a>\n" +
                    "        <a href=\"../../static/image/karyoty/Solidago_caesia.png\" target=\"_blank\"  class=\"bi bi-eye\"></a>\n" +
                    "    </div>\n" +
                    "</div>",
            },
            {
                "id": 2,
                "parentId": 1,
                "text": "<div class=\"row\">\n" +
                    "    <div class=\"col-lg-10\">\n" +
                    "        <p style=\"margin-bottom: 5px\">Solidago canadensis\n</p>\n" +
                    "    </div>\n" +
                    "    <div class=\"col-lg-2\" style=\"padding: 0\">\n" +
                    "        <a href=\"karyotype/Solidago_canadensis\" target=\"_blank\" class=\"bi bi-caret-right\"></a>\n" +
                    "        <a href=\"../../static/image/karyoty/Solidago_canadensis.png\" target=\"_blank\"  class=\"bi bi-eye\"></a>\n" +
                    "    </div>\n" +
                    "</div>",
            },
            {
                "id": 2,
                "parentId": 1,
                "text": "<div class=\"row\">\n" +
                    "    <div class=\"col-lg-10\">\n" +
                    "        <p style=\"margin-bottom: 5px\">Stevia rebaudiana\n</p>\n" +
                    "    </div>\n" +
                    "    <div class=\"col-lg-2\" style=\"padding: 0\">\n" +
                    "        <a href=\"karyotype/Stevia_rebaudiana\" target=\"_blank\" class=\"bi bi-caret-right\"></a>\n" +
                    "        <a href=\"../../static/image/karyoty/Stevia_rebaudiana.png\" target=\"_blank\"  class=\"bi bi-eye\"></a>\n" +
                    "    </div>\n" +
                    "</div>",
            },
            {
                "id": 2,
                "parentId": 1,
                "text": "<div class=\"row\">\n" +
                    "    <div class=\"col-lg-10\">\n" +
                    "        <p style=\"margin-bottom: 5px\">Tagetes erecta\n</p>\n" +
                    "    </div>\n" +
                    "    <div class=\"col-lg-2\" style=\"padding: 0\">\n" +
                    "        <a href=\"karyotype/Tagetes_erecta\" target=\"_blank\" class=\"bi bi-caret-right\"></a>\n" +
                    "        <a href=\"../../static/image/karyoty/Tagetes_erecta.png\" target=\"_blank\"  class=\"bi bi-eye\"></a>\n" +
                    "    </div>\n" +
                    "</div>",
            },
            {
                "id": 2,
                "parentId": 1,
                "text": "<div class=\"row\">\n" +
                    "    <div class=\"col-lg-10\">\n" +
                    "        <p style=\"margin-bottom: 5px\">Taraxacum mongolicum\n</p>\n" +
                    "    </div>\n" +
                    "    <div class=\"col-lg-2\" style=\"padding: 0\">\n" +
                    "        <a href=\"karyotype/Taraxacum_mongolicum\" target=\"_blank\" class=\"bi bi-caret-right\"></a>\n" +
                    "        <a href=\"../../static/image/karyoty/Taraxacum_mongolicum.png\" target=\"_blank\"  class=\"bi bi-eye\"></a>\n" +
                    "    </div>\n" +
                    "</div>",
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