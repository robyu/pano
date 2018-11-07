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

function onImageClick(popname, btn_index, num_images, curr_image) {
    pop_element = document.getElementById(popname)

    if (btn_index<=0) {
        prev_onclick = "" 
    }
    else {
        prev_onclick = "navigateToImage(" + (btn_index-1).toString() + ");"
    }

    if (btn_index>=num_images-1) {
        next_onclick = ""
    }
    else {
        next_onclick = "navigateToImage(" + (btn_index+1).toString() + ");"
    }
    
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
    html = html + "        <p class=\"text-center\">"

    /* 
       the prev and next button work by calling navigateToImage(), which simulates clicking on the previous or 
       next image's button
    */
    html = html + "          <button class=\"btn\" onclick=\"" + prev_onclick + "\"> (<< prev) </button>"
    /*
      goddamn I hate javascript:
      can't embed escaped quotes in tags, need to replace quotes with &quot;
    */
    //h =           "          <button class=\"btn\" onclick=\"console.info(&quot;goddamn&quot;)\" > (X close)  </button>"
    h =           "          <button class=\"btn\" onclick=\"closePopWindow(&quot;" + popname + "&quot;)\" > (X close)  </button>"
    html = html + h
    html = html + "          <button class=\"btn\" onclick=\"" + next_onclick + "\"> (next >>)  </button>"
    html = html + "        </p>"
    html = html + "        <div class=\"container border border-primary\">"
    html = html + "            <a href=\"" +curr_image+ "\">"
    html = html + "                <img src=\" "+curr_image+ "\" class=\"img-fluid d-block mx-auto\">"
    html = html + "            </a>"
    html = html + "        </div>"  // container
    html = html + "      </div>"
    html = html + "      <div class=\"col-sm-1\">"
    html = html + "      </div>"
    html = html + "    </div>"  // row
    //html = html + "</div>" // row
    pop_element.innerHTML = html;

    /* set display property to block: take up whole width */
    pop_element.style.display="block";

    /* close window when clicked */
    // pop_element.onclick = (function (onclick) {
    //     return function(evt) {
    //         // reference to event to pass argument properly
    //         evt  = evt || event;

    //         // onClick even still works in the DOM
    //         if (onclick) {
    //             onclick(evt);
    //         }
    //         // new code that will happen when you click only if you click on the background.
    //         if (evt.target == pop_element) { pop_element.style.display="none"; } 
    //     }
    // })(pop_element.onclick);
} 

/*
open specified image index in pop window
same as clicking on an image's button to open it in the pop window
*/
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

/* 
close the pop window
*/
function closePopWindow(popname) {
    document.getElementById(popname).style.display="none";
    document.getElementById(popname).innerHTML = ""; 
}         

//var element = document.getElementById("video_pop");

