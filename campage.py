
import datastore
import time
import os
import dtutils
import pudb
import logging
import tempfile
"""

  
"""
class CamPage:
    #
    # {navbar_html}
    # {carousel_body_html}
    # {media_rows_html}
    templ_header_body_footer = unicode("""
<!DOCTYPE html>
<html>
    <head>
        <!-- Required meta tags -->
        <meta charset="utf-8">
        <meta name="viewport" content="width=device-width, initial-scale=1, shrink-to-fit=no">

        <title>Panopticon Media</title>
        <meta name="description" content="panopticon">
        <meta name="author" content="Robert Yu, Buttersquid Inc">
        <META HTTP-EQUIV="refresh" CONTENT="300"> 

        <link rel="stylesheet" href="https://maxcdn.bootstrapcdn.com/bootstrap/4.0.0/css/bootstrap.min.css" integrity="sha384-Gn5384xqQ1aoWXA+058RXPxPg6fy4IWvTNh0E263XmFcJlSAwiGgFAW/dAiS6JXm" crossorigin="anonymous">
	<link rel="stylesheet" href="css/styles.css">

    </head>
    <body>
        
        {navbar_html}

        <!-- pop-up video player is always at top -->
        <div class="container-fluid" id="display-container"> <!-- container-fluid takes up 100% of viewport -->
            <!-- put the video player in the div above the image and video columns  -->
            <div class="video-pop-up" id="video_pop0" >
                div_video_pop0
            </div>
        </div>

        {carousel_body_html}
            
        <!-- media rows -->
        <div class="container-fluid"> <!-- container-fluid takes up 100% of viewport -->
            {media_rows_html}
        </div>
            
        <!-- footer -->
        <script src="https://code.jquery.com/jquery-3.2.1.slim.min.js" integrity="sha384-KJ3o2DKtIkvYIK3UENzmM7KCkRr/rE9/Qpg6aAZGJwFDMVNA/GpGFF93hXpG5KkN" crossorigin="anonymous"></script>
        <script src="https://cdnjs.cloudflare.com/ajax/libs/popper.js/1.12.9/umd/popper.min.js" integrity="sha384-ApNbgh9B+Y1QKtv3Rn7W3mgPxhU9K/ScQsAP7hUibX39j7fakFPskvXusvfa0b4Q" crossorigin="anonymous"></script>
        <script src="https://maxcdn.bootstrapcdn.com/bootstrap/4.0.0/js/bootstrap.min.js" integrity="sha384-JZR6Spejh4U02d8jOt6vLEHfe/JQGiRRSQQxSfFWpi1MquVdAyjUar5+76PVCmYl" crossorigin="anonymous"></script>
        <script src="js/scripts.js"></script>
    </body>
</html>
    """)

    #
    # {cam_name} = camera name
    # {url_next_page} = URL of next cam page
    # {url_prev_page} = URL of prev cam page
    templ_navbar_html=unicode("""
        <!-- A grey horizontal navbar that becomes vertical on small screens -->
        <nav class="navbar navbar-expand-sm bg-dark sticky-top">

            <!-- Links -->
            <ul class="navbar-nav">
                <li class="nav-item">
                    <a class="nav-link" href="{url_prev_page}"> &lt&ltprev</a> <!-- can't use actual'lessthan' character -->
                </li>
                <li class="nav-item">
                    <!-- TODO: figure out how to do collapse('show') after loading page -->
                    <a class="nav-link" href="index.html#button-{cam_name}">^up^</a>
                </li>
                <li class="nav-item">
                    <a class="nav-link" href="{url_next_page}">next>></a>
                </li>
            </ul>
        </nav>
""")

    #
    # {cam_name}
    # {carousel_images_html}
    templ_carousel_body_html=unicode("""
        <!-- carousel -->
        <div class="container-fluid" >
            <div class="row">
                <div class="col-sm">
                    <div class="card mt-2 mb-2" >
                        <h5 class="card-title">Camera {cam_name}</h5>
                    </div>
		</div>
                <div class="col-sm">
                    <div id="carouselThumbnails" class="carousel slide mt-2 mb-2" data-ride="carousel">
                        <div class="carousel-inner">
                           {carousel_images_html}
                        </div>
                        <a class="carousel-control-prev" href="#carouselThumbnails" role="button" data-slide="prev">
                            <span class="carousel-control-prev-icon" aria-hidden="true"></span>
                            <span class="sr-only">Previous</span>
                        </a>
                        <a class="carousel-control-next" href="#carouselThumbnails" role="button" data-slide="next" >
                            <span class="carousel-control-next-icon" aria-hidden="true"></span>
                            <span class="sr-only">Next</span>
                        </a>
                    </div>
                </div>
                <div class="col-sm">

                </div>
            </div>
        </div>
""")

    #
    # "first" template has class "active" to indicate initial image
    #
    # {image_url}
    # {image_date_time}
    templ_carousel_image_first=unicode("""
                            <div class="carousel-item active"> <!-- first item has class 'active' -->
                                <img class="d-block w-100" src="{image_url}" alt="{image_date_time}">
				<div class="carousel-caption" >
				    <p>{image_date_time}</p>
				</div>
                            </div>
    """)

    #{image_url}
    #{image_date_time}
    templ_carousel_image=unicode("""
                            <div class="carousel-item">
                                <img class="d-block w-100" src="{image_url}" alt="{image_date_time}">
				<div class="carousel-caption d-none d-md-block" >
				    <p>{image_date_time}</p>
				</div>
                            </div>
    """)


            # <!-- TEMPLATE START media-row
            #      placeholders:
            #      {upper_datetime} - stop time
            #      {lower_datetime} - start time
            #      {html_images}
            #      {html_videos}
            # -->
    templ_media_row = unicode("""
            <div class="row" >
                <h3 class="row-date-range">
                    {lower_datetime} .. {upper_datetime}
                </h3>
            </div>
            
            <div class="row">
                <!-- thumbnail column -->
                <div class="col-sm-10 border-right border-success">
                    <!-- insert image html here -->
                    {html_images}
                </div>
                <!-- video column -->
                <div class="col-sm-2">
                    <!-- insert videos here  -->
                    {html_videos}
                </div>
            </div>
    """)

    
                    # <!-- TEMPLATE START image_link
                         
                    #      placeholders:
                    #      {thumb_image}
                    #      {alt_txt}
                    #      {actual_image}
                    # -->
    templ_image_link=unicode("""
                    <a href="{actual_image}"><img class="thumbnail" alt="{alt_txt}" src="{thumb_image}" ></a>
    """)

                    # <!-- TEMPLATE START video_link
                    #      placeholders:
                    #      {actual_video}
                    #      {lower_time}
                    # -->
    templ_video_link=unicode("""
                    <p>
                        <button class="btn btn-outline-success" type="button" onclick="onVideoClick('{actual_video}','video_pop0');">
                            {lower_time}
                        </button>
                    </p>
    """)

    def __init__(self,
                 camera_name,
                 db,
                 derived_dir,
                 base_dir,
                 www_dir,
                 www_derived_dir,
                 www_base_dir):
        """
        camera_name = "whatever"
        db = the image datastore
        derived_dir = the actual path to the "derived" media, e.g. "/media/derived"
        base_dir = the actual path to the actual media, e.g. "/media/FTP"
        www_dir = actual path to webserver directory, e.g. "www"
        www_derived_dir = path to webserver directory for derived media, e.g. "www/derived"
        www_base_dir = path to webserver directory for actual media, e.g. "www/FTP"
        """
        
        self.db = db  # pointer to datastore
        self.derived_dir = derived_dir
        os.path.exists(derived_dir)
        
        self.base_dir = base_dir
        os.path.exists(base_dir)
        
        self.www_derived_dir = www_derived_dir
        os.path.exists(www_derived_dir)
        
        self.www_base_dir = www_base_dir
        os.path.exists(www_base_dir)
        
        self.num_images_per_row = 4

        self.www_dir = www_dir
        assert os.path.exists(self.www_dir)

        self.default_image_fname = os.path.join(self.www_dir, 'mryuck.png')
        assert os.path.exists(self.default_image_fname)

        self.camera_name = camera_name

        #
        # composing the webpage can take substantial time, so
        # compose HTML in a temporary file, then
        # rename it to final dest fname.
        self.max_images_per_page = 50
        self.fname_index=0

        self.logger = logging.getLogger(__name__)

    def calc_dest_fname(self, last_flag=False):
        """
        generate filenames of media pages
        based on fname counter (self.fname_index)

        IN: 
        last_flag - True if this is the last media page
        
        RETURNS:
        dest_fname, prev_fname, next_fname
        """
        dest_fname = "%s-%04d.html" % (self.camera_name, self.fname_index)

        if self.fname_index==0:
            prev_fname = ""
        else:
            prev_fname = "%s-%04d.html" % (self.camera_name, self.fname_index - 1)

        if last_flag==False:
            next_fname = "%s-%04d.html" % (self.camera_name, self.fname_index + 1)
        else:
            next_fname = ""
            
        self.fname_index += 1
        return dest_fname, prev_fname, next_fname
        
    def write_html(self,dest_fname, html_doc):
        """
        given destination fname and html text,
        write HTML file

        returns:
        none
        """ 
        temp_fname = os.path.join(self.www_dir, tempfile.mktemp('.html'))
        f = open(temp_fname, "wt")
        f.write(html_doc)
        f.close()
        
        #
        # remove existing dest_fname, rename temp to dest_fname
        full_dest_fname = os.path.join(self.www_dir, dest_fname)
        if os.path.exists(full_dest_fname):
            os.remove(full_dest_fname)
        #end

        os.rename(temp_fname, full_dest_fname)
        
    
    def add_html_header_footer(self, html_doc, url_prev_page, url_next_page):
        """
        given html text, url of previous page, url of next page,
        return html text with HTML header and footer

        the header template is filled with the URLs of the previous and next media pages
        """
        new_html =CamPage.templ_header.format(cam_name=self.camera_name,
                                              url_next_page = url_next_page,
                                              url_prev_page = url_prev_page) + html_doc
        new_html = new_html + CamPage.templ_footer
        return new_html
        
        
    def get_thumb_path(self, row):
        """
        return the path to the derived image/video file
        OR a default image (if the derived file does not exist)
        """
        if len(row.d['derived_fname']) == 0:   # no thumbnail
            thumb_path = self.default_image_fname
        else:
            thumb_path = row.d['derived_fname']
        #end

        if os.path.exists(thumb_path)==False:
            self.logger.info("%s does not exist" % thumb_path)
            thumb_path = self.default_image_name
        #end
        thumb_path2 = thumb_path.replace(self.derived_dir, self.www_derived_dir)
        return thumb_path2

    def get_actual_path(self, row):
        """
        return the path to the actual image/video source file
        """
        actual_path = os.path.join(self.base_dir, row.d['path'], row.d['fname'])

        if os.path.exists(actual_path)==False:
            self.logger.info("%s does not exist" % actual_path)
            actual_path = self.default_image_name
        #end
        
        # replace basedir with webpage-friendly path
        # ./FTP/120/AMC0028V_795UUB/2018-08-24/001/jpg/22/27/22[M][0@0][0].jpg
        actual_path2 = actual_path.replace(self.base_dir, self.www_base_dir)
        
        return actual_path2
    
        
    # <a href="https://www.w3schools.com">
    # <img border="0" alt="W3Schools" src="logo_w3s.gif" width="100" height="100">
    # </a>
    def make_html_image_list(self, image_row_list):
        """
        given a list of row elements representing images,
        return HTML for a single row
        """
        html = ''
        n = 0

        #
        # make a single row of (num_images_per_row) images
        while n+self.num_images_per_row <= len(image_row_list):
            for m in range(self.num_images_per_row):
                row = image_row_list[n+m]
                thumb_path  = self.get_thumb_path(row)
                actual_path = self.get_actual_path(row)
                html += CamPage.templ_image_link.format(actual_image=actual_path,
                                                        alt_txt=row.d['ctime'],
                                                        thumb_image=thumb_path)
            #end
            n += self.num_images_per_row
        #end
        assert len(image_row_list) - n < self.num_images_per_row

        #
        # make a row of the remaining imagees
        while n < len(image_row_list):
            row = image_row_list[n]
            thumb_path  = self.get_thumb_path(row)
            actual_path = self.get_actual_path(row)
            html += CamPage.templ_image_link.format(actual_image=actual_path,
                                                    alt_txt=row.d['ctime'],
                                                    thumb_image=thumb_path)
            n += 1
        #end
        assert n==len(image_row_list)
        return html

    def make_html_video_list(self, video_row_list):
        """
        given a list of row elements representing videos,
        return HTML for a single row
        """
        html = ''
        n = 0
        
        while n < len(video_row_list):
            row = video_row_list[n]
            if len(row.d['derived_fname']) <= 0:
                n += 1
                continue
            #else...
            video_fname = row.d['derived_fname']
            video_fname = video_fname.replace(self.derived_dir, self.www_derived_dir)
            lower_time = dtutils.sec_to_str(row.d['ctime_unix'],"%H:%M:%S")
            html += CamPage.templ_video_link.format(actual_video=video_fname,
                                                    lower_time=lower_time)
            n += 1
        #end
        return html

    def gen_row_html(self, html_images, html_videos, upper_datetime, lower_datetime,media_row_index):
        """
        given 
        html_images: html listing images
        html_videos: html listing videos
        upper_datetime:  string specifying start datetime
        lower_datetime: string specifying stop datetime

        return HTML for a single row
        """
        html = CamPage.templ_media_row.format(upper_datetime = upper_datetime,
                                              lower_datetime = lower_datetime,
                                              html_images = html_images,
                                              html_videos = html_videos,
                                              index=media_row_index)
        return html

    def make_status_dict(self, dest_fname, upper_time_sec, lower_time_sec):
        """
        make dictionary entry with generated HTML files and associated times
        """
        d={}
        assert upper_time_sec >= lower_time_sec
        d['page_fname'] = dest_fname
        d['upper_time_sec'] = upper_time_sec
        d['lower_time_sec'] = lower_time_sec
        return d

    def make_html_navbar(self, prev_fname, next_fname):
        html = CamPage.templ_navbar_html.format(cam_name=self.camera_name,
                                                url_next_page = next_fname,
                                                url_prev_page = prev_fname)
        return html
    
    
    def make_html_doc(self, carousel_html, media_html, navbar_html):
        carousel_body_html = CamPage.templ_carousel_body_html.format(carousel_images_html = carousel_html,
                                                                     cam_name = self.camera_name)
        html_doc = CamPage.templ_header_body_footer.format(navbar_html = navbar_html,
                                                           carousel_body_html = carousel_body_html,
                                                           media_rows_html = media_html)
        return html_doc


    
    def write_webpage(self, carousel_html, media_html, is_last):
        """
        write actual HTML file, return filename

        in:
        carousel_html - html for image carousel
        media_html - html for image/video rows
        is_last = True when this is final webpage for current camera

        returns:
        filename
        """
        dest_fname, prev_fname, next_fname = self.calc_dest_fname(last_flag=is_last)
        navbar_html = self.make_html_navbar(prev_fname, next_fname)
        html_doc = self.make_html_doc(carousel_html, media_html, navbar_html)
        self.write_html(dest_fname, html_doc)

        return dest_fname

    def make_html_carousel(self, image_list, row_index):
        """
        given 
        image_list - list of datastore image entries
        row_index - integer indicating media row index

        return HTML with carousel images

        does NOT return the carousel body; carousel body is formed just prior to writing webpage
        """
        assert len(image_list) > 0

        if row_index==0:
            thumb_path = self.get_thumb_path(image_list[0])
            image_dt = dtutils.sec_to_str(image_list[0].d['ctime_unix'],"%H:%M:%S")
            rows_html = CamPage.templ_carousel_image_first.format(image_url = thumb_path,
                                                                 image_date_time = image_dt)
            startindex=1  # start index for remaining loop
        else:
            rows_html = ''
            startindex=0  # start indx for remaining loop
        #end

        for m in range(startindex, len(image_list)):
            thumb_path = self.get_thumb_path(image_list[m])
            image_dt = dtutils.sec_to_str(image_list[m].d['ctime_unix'],"%H:%M:%S")
            rows_html += CamPage.templ_carousel_image.format(image_url = thumb_path,
                                                             image_date_time = image_dt)
        #end

        return rows_html
    
    def make_html_media_row(self, image_list, video_list, upper_time_sec, lower_time_sec):
        """
        return HTML for a single media row (images + video)
        """
        upper_timefmt = "%a %b %d %H:%M:%S"
        lower_timefmt = "%H:%M:%S"

        images_html  = self.make_html_image_list(image_list)
        videos_html  = self.make_html_video_list(video_list)
        upper_datetime = dtutils.sec_to_str(upper_time_sec, lower_timefmt)
        lower_datetime = dtutils.sec_to_str(lower_time_sec, upper_timefmt)
        row_html = CamPage.templ_media_row.format(upper_datetime = upper_datetime,
                                                  lower_datetime = lower_datetime,
                                                  html_images = images_html,
                                                  html_videos = videos_html)

        return row_html
        
    
    def generate(self, upper_datetime, max_age_days, interval_min):
        """
        given
        upper_datetime: starting datetime string
        max_age_days: maximum number of days to include in webpage
        interval_min: time interval for each row in webpage

        generates 1 or more camera status webpages

        RETURNS
        status_page_list:  list of dictionary elements
        each dict has keys:
        'page_fname' : NOT preceded with www_dir, e.g. camera0_000.html and NOT www/camera0_000.html
        'upper_time_sec'
        'lower_time_sec'

        """
        status_page_list = []
        #
        # convert and compute datetime intervals in seconds
        upper_time_sec = self.db.iso8601_to_sec(upper_datetime)
        assert upper_time_sec > 0

        final_lower_time_sec = upper_time_sec - int(max_age_days * 24.0 * 60.0 * 60.0) # days * (hrs/day)(min/hrs)(sec/min)
        assert (final_lower_time_sec > 0)

        assert interval_min > 0
        interval_sec = int(interval_min * 60.0)

        # start a new web page
        media_row_index = 0
        carousel_html = ''
        media_html = ''

        # iterate through all rows which fall into the time interval
        # iterate backwards through time, from latest (upper time) to oldest (lower time)
        num_images_per_page = 0
        curr_file_upper_time_sec = -1
        while(upper_time_sec > final_lower_time_sec):
            lower_time_sec = upper_time_sec - interval_sec
            row_image_list = self.db.select_by_time_cam_media(self.camera_name,
                                                         upper_time_sec,
                                                         lower_time_sec,
                                                         mediatype=datastore.MEDIA_IMAGE)
            row_video_list = self.db.select_by_time_cam_media(self.camera_name,
                                                         upper_time_sec,
                                                         lower_time_sec,
                                                         mediatype=datastore.MEDIA_VIDEO)
            if (len(row_image_list)>0) or (len(row_video_list)>0):
                #
                # if upper_time0 not yet recorded, then do so
                if curr_file_upper_time_sec <= 0:
                    curr_file_upper_time_sec = upper_time_sec
                if len(row_image_list) > 0:
                    carousel_html += self.make_html_carousel(row_image_list, media_row_index)
                #end
                media_html += self.make_html_media_row(row_image_list, row_video_list, upper_time_sec, lower_time_sec)
                media_row_index += 1
                num_images_per_page += max(len(row_image_list), len(row_video_list))
                
                if num_images_per_page >= self.max_images_per_page:
                    #
                    # close current webpage
                    dest_fname = self.write_webpage(carousel_html, media_html, False)
                    status_page_list.append(self.make_status_dict(dest_fname, curr_file_upper_time_sec, lower_time_sec))
                    
                    #
                    # start a new webpage
                    media_row_index=0
                    carousel_html = ''
                    media_html = ''
                    num_images_per_page = 0

                    # reset upper_time
                    curr_file_upper_time_sec = -1
                #end 
            #end
            upper_time_sec = lower_time_sec
        #end
        
        # close current file
        dest_fname = self.write_webpage(carousel_html, media_html, True)
        status_page_list.append(self.make_status_dict(dest_fname, curr_file_upper_time_sec, lower_time_sec))

        #
        # for next time around, restart the suffix index
        self.fname_index=0
        
        return status_page_list

