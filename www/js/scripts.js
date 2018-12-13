/*
2018 Robert Yu
*/

/*
pop up video player with download link

assign onclick handler to close the window
*/
function onVideoClick(mp4_fname,dav_fname,popname) {
    pop_element = document.getElementById(popname)

    html =        "<div>"
    html = html + "    <video controls autoplay loop id=\"pano_video_player\"><source src=\""+mp4_fname+"\" type=\"video/webm\"></video>";
    html = html + "</div>";
    html = html + "<div>";
    html = html + "    <a href=" + mp4_fname + "> direct link >>" + mp4_fname + "</a>";
    html = html + "<div>";
    html = html + "    <a href=" + dav_fname + "> direct link >>" + dav_fname + "</a>";
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

/*

button onclick function to unhide the image display element
and display an image

popname - name of pop-up image display element
image_index - integer index of this image
num_images - number of images on this webpage
image_url - image to display 
*/
function onImageClick(popname, image_index, num_images, image_url) {
    pop_element = document.getElementById(popname)

    if (image_index<=0) {
        prev_onclick = "";
    }
    else {
        prev_onclick = "navigateToImage(" + (image_index-1).toString() + ");";
    }

    if (image_index>=num_images-1) {
        next_onclick = "";
    }
    else {
        next_onclick = "navigateToImage(" + (image_index+1).toString() + ");";
    }
    console.info("== INDEX " + image_index);
    console.info("prev_onclick=" + prev_onclick);
    console.info("next_onclick=" + next_onclick);
    
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
       the prev and next buttons work by calling navigateToImage(), which simulates clicking on the previous or 
       next image's button
    */
    html = html + "          <button class=\"btn btn-outline-success pop-nav-btn\" onclick=\"" + prev_onclick + "\"> << later </button>"
    /*
      goddamn I hate javascript:
      can't embed escaped quotes in tags, need to replace quotes with &quot;
    */
    h =           "          <button class=\"btn btn-outline-success pop-nav-btn\" onclick=\"closePopWindow(&quot;" + popname + "&quot;)\" > X close  </button>"
    html = html + h
    html = html + "          <button class=\"btn btn-outline-success pop-nav-btn\" onclick=\"" + next_onclick + "\"> earlier >> </button>"
    html = html + "        </p>"
    html = html + "        <div class=\"container border border-success\">"
    html = html + "            <a href=\"" +image_url+ "\">"
    html = html + "                <img src=\" "+image_url+ "\" class=\"img-fluid d-block mx-auto\">"
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
    dest_id = "btn-image-" + dest_index.toString()
    button = document.getElementById(dest_id);
    button.click();
}

/* 
close the pop window
*/
function closePopWindow(popname) {
    document.getElementById(popname).style.display="none";
    document.getElementById(popname).innerHTML = ""; 
}         

//var element = document.getElementById("video_pop");

