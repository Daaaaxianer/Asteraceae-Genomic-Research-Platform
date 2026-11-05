
document.addEventListener('DOMContentLoaded', function() {

    var dropdownElementList = [].slice.call(document.querySelectorAll('.dropdown-toggle'))
    var dropdownList = dropdownElementList.map(function (dropdownToggleEl) {
        return new bootstrap.Dropdown(dropdownToggleEl)
    });


    var multiLevelDropdowns = document.querySelectorAll('.dropdown-menu .dropdown-toggle');

    multiLevelDropdowns.forEach(function(dropdown) {
        dropdown.addEventListener('click', function(e) {
            e.preventDefault();
            e.stopPropagation();

            var submenu = this.nextElementSibling;
            if (submenu && submenu.classList.contains('dropdown-menu')) {


                var isShowing = submenu.classList.contains('show');


                document.querySelectorAll('.dropdown-menu .dropdown-menu').forEach(function(menu) {
                    menu.classList.remove('show');
                });


                if (!isShowing) {
                    submenu.classList.add('show');
                }


                adjustSubmenuPosition(submenu);
            }
        });
    });


    document.addEventListener('click', function(e) {
        if (!e.target.matches('.dropdown-toggle') && !e.target.closest('.dropdown-menu')) {
            document.querySelectorAll('.dropdown-menu .dropdown-menu').forEach(function(menu) {
                menu.classList.remove('show');
            });
        }
    });


    var dropdownItems = document.querySelectorAll('.dropend');
    dropdownItems.forEach(function(item) {
        item.addEventListener('mouseenter', function() {
            var submenu = this.querySelector('.dropdown-menu');
            if (submenu) {
                submenu.classList.add('show');
                adjustSubmenuPosition(submenu);
            }
        });

        item.addEventListener('mouseleave', function(e) {
            var submenu = this.querySelector('.dropdown-menu');
            if (submenu) {
                setTimeout(function() {
                    if (!submenu.matches(':hover') && !item.matches(':hover')) {
                        submenu.classList.remove('show');
                    }
                }, 150);
            }
        });
    });
});


function adjustSubmenuPosition(submenu) {
    var rect = submenu.getBoundingClientRect();
    var viewportWidth = window.innerWidth;


    if (rect.right > viewportWidth - 20) {
        submenu.style.left = 'auto';
        submenu.style.right = '100%';
    } else {
        submenu.style.left = '';
        submenu.style.right = '';
    }
}
