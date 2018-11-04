/*
pop up video player with download link

assign onclick handler to close the window
*/
function onVideoClick(theLink,popname) {
    pop_element = document.getElementById(popname)

    html =        "<div>"
    html = html + "    <video controls autoplay loop id=\"pano_video_player\"><source src=\""+theLink+"\" type=\"video/webm\"></video>";
    html = html + "</div>";
    html = html + "<div>";
    html = html + "    <a href=" + theLink + "> direct link >>" + theLink + "</a>";
    html = html + "</div>";
    pop_element.innerHTML = html;

    /* set display property to block: take up whole width */
    pop_element.style.display="block";

    /* close window when clicked */
    pop_element.onclick = (function (onclick) {
        return function(evt) {
            // reference to event to pass argument properly
            evt  = evt || event;

            // onClick even still works in the DOM
            if (onclick) {
                onclick(evt);
            }
            // new code that will happen when you click only if you click on the background.
            if (evt.target == pop_element) { pop_element.style.display="none"; } 
        }
    })(pop_element.onclick);

} 

function onImageClick(popname, btn_index, curr_image) {
    pop_element = document.getElementById(popname)

    /*
      bootstrap classes:
      img-fluid makes the image responsive
      d-block mx-auto centers the image
    */
    html = ""
    //html = ahtml + "<div class=\"row\">"
    html = html + "    <div class=\"row\">"
    html = html + "      <div class=\"col-sm-1\">"
    html = html + "      </div>"
    html = html + "      <div class=\"col-sm-10\">"
    html = html + "        <div class=\"container border border-primary\">"
    html = html + "            <img src=\" "+curr_image+ "\" class=\"img-fluid d-block mx-auto\">"
    html = html + "        </div>"  // container
    html = html + "      </div>"
    html = html + "      <div class=\"col-sm-1\">"
    html = html + "        <button class=\"btn\" onclick=\"navigateToImage(001);\"> (next)  </button>"
    html = html + "      </div>"
    html = html + "    </div>"  // row
    //html = html + "</div>" // row
    pop_element.innerHTML = html;

    /* set display property to block: take up whole width */
    pop_element.style.display="block";

    /* close window when clicked */
    pop_element.onclick = (function (onclick) {
        return function(evt) {
            // reference to event to pass argument properly
            evt  = evt || event;

            // onClick even still works in the DOM
            if (onclick) {
                onclick(evt);
            }
            // new code that will happen when you click only if you click on the background.
            if (evt.target == pop_element) { pop_element.style.display="none"; } 
        }
    })(pop_element.onclick);

} 

function navigateToImage(dest_index) {

    /*
      convert 3 -> 003
    */
    dest_index_str = dest_index.toString()
    MAX_LEN = 3
    len = dest_index_str.length
    for (n=0;n<MAX_LEN - len;n++) {
        dest_index_str = '0' + dest_index_str
    }

    dest_id = "btn-image-" + dest_index_str
    button = document.getElementById(dest_id)
    button.click()
}

// function onPopClick() {
//     document.getElementById("video_pop").style.display="none";
//     document.getElementById("video_pop").innerHTML = ""; 
// }         

//var element = document.getElementById("video_pop");

