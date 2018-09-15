/*
pop up video player with download link

assign onclick handler to close the window
*/
function onVideoClick(theLink,popname) {
    pop_element = document.getElementById(popname)

    html = "<div>"
    html = html + "<video controls autoplay loop id=\"the_Video\"><source src=\""+theLink+"\" type=\"video/webm\"></video>";
    html = html + "</div>";
    html = html + "<div>";
    html = html + "<a href=" + theLink + "> direct link >>" + theLink + "</a>";
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

// function onPopClick() {
//     document.getElementById("video_pop").style.display="none";
//     document.getElementById("video_pop").innerHTML = ""; 
// }         

//var element = document.getElementById("video_pop");

