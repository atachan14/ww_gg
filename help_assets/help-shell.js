"use strict";const book=document.querySelector(`[data-book="${document.body.dataset.helpPage}"]`);if(book){book.setAttribute('aria-current','page');const parent=book.closest('details');if(parent)parent.open=true;}
document.addEventListener("keydown",e=>{if((e.key==="ArrowLeft"||e.key==="ArrowRight")&&e.target.closest(".bookshelf,.breadcrumbs,.site-head"))e.stopPropagation();},true);
