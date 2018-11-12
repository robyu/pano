
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
        <META HTTP-EQUIV="refresh" CONTENT="600"> 

        <link rel="stylesheet" href="https://maxcdn.bootstrapcdn.com/bootstrap/4.0.0/css/bootstrap.min.css" integrity="sha384-Gn5384xqQ1aoWXA+058RXPxPg6fy4IWvTNh0E263XmFcJlSAwiGgFAW/dAiS6JXm" crossorigin="anonymous">
	<link rel="stylesheet" href="css/styles.css">

    </head>
    <body>
        
        {navbar_html}

        <!-- pop-up video player is always at top -->
        <div class="container-fluid" id="display-container"> <!-- container-fluid takes up 100% of viewport -->
            <!-- put the video player in the div above the image and video columns  -->
            <div class="display-pop-up" id="video_pop0" >
                div_video_pop0
            </div>
            <div class="display-pop-up" id="image_pop0" >
                div_image_pop0
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
                <!-- specify "border border-success rounded" to make links look button-ish -->
                <li class="nav-item border border-success rounded">
                    <a class="nav-link" href="{url_prev_page}"> &lt&ltprev</a> <!-- can't use actual'lessthan' character -->
                </li>
                <li class="nav-item border border-success rounded">
                    <!-- TODO: figure out how to do collapse('show') after loading page -->
                    <a class="nav-link" href="index.html#button-{cam_name}">^all cams^</a>
                </li>
                <li class="nav-item border border-success rounded">
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
            #      {later_datetime} - stop time
            #      {earlier_datetime} - start time
            #      {html_images}
            #      {html_videos}
            # -->
    templ_media_row = unicode("""
            <div class="row" >
                <h5 class="row-date-range">
                    {earlier_datetime} .. {later_datetime}
                </h5>
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
                    #      {image_index} - zero-padded 3 digit
                    #      {max_num_images}
                    #      {thumb_image}
                    #      {alt_txt}
                    #      {actual_image}
                    # -->
    # templ_image_link=unicode("""
    #                 <a href="{actual_image}"><img class="thumbnail" alt="{alt_txt}" src="{thumb_image}" ></a>
    # """)
    templ_image_link=unicode("""
                    <button class="btn pano-image-button" type="button" id="btn-image-{image_index}" onclick="onImageClick('image_pop0', {image_index}, {max_num_images}, '{actual_image}');">
                        <img class="thumbnail" alt="{alt_txt}" src="{thumb_image}" >
                    </button>
    """)
    

                    # <!-- TEMPLATE START video_link
                    #      placeholders:
                    #      {actual_video}
                    #      {earlier_time}
                    # -->
    templ_video_link=unicode("""
                    <p>
                        <button class="btn btn-outline-success" type="button" onclick="onVideoClick('{actual_video}','video_pop0');">
                            {earlier_time}
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
        assert os.path.exists(derived_dir), "derived_dir does not exist: %s" % derived_dir
        
        self.base_dir = base_dir
        assert os.path.exists(base_dir), "base_dir does not exist: %s" % base_dir
        
        self.www_derived_dir = www_derived_dir
        
        self.www_base_dir = www_base_dir
        
        self.num_images_per_row = 4

        self.www_dir = www_dir

        self.default_image_fname = os.path.join(self.www_dir, 'mryuck.png')
        assert os.path.exists(self.default_image_fname)

        self.camera_name = camera_name

        #
        # composing the webpage can take substantial time, so
        # compose HTML in a temporary file, then
        # rename it to final dest fname.
        self.max_images_per_page = 200
        self.fname_index=0

        #
        # generate carousel html?
        self.make_carousel=False

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
    def make_html_image_list(self, image_row_list, image_index_offset):
        """
        given a list of row elements representing images,
        return HTML for a single row
        """
        html = ''
        n = 0

        #
        # augment image list with a running index
        # index is used for in-page navigation
        for m in range(len(image_row_list)):
            image_row_list[m].d['image_index'] = m + image_index_offset
        #end


        #
        # stupid javascript alert:
        # the image_index CANNOT be specified as a zero-padded index,
        # because javascript cleverly interprets integers of the form 0nnn
        # as octal.  fuck Brendan Eich.
        
        #
        # if there are enough images for a full row, then make a full row
        while n+self.num_images_per_row <= len(image_row_list):
            for m in range(self.num_images_per_row):
                image = image_row_list[n+m]
                thumb_path  = self.get_thumb_path(image)
                actual_path = self.get_actual_path(image)
                html += CamPage.templ_image_link.format(actual_image=actual_path,
                                                        alt_txt=image.d['ctime'],
                                                        thumb_image=thumb_path,
                                                        image_index=image.d['image_index'], # unique HTML ID for each image
                                                        max_num_images="{max_index}")
            #end
            n += self.num_images_per_row
        #end
        assert len(image_row_list) - n < self.num_images_per_row

        #
        # make a row of the remaining images
        while n < len(image_row_list):
            image = image_row_list[n]
            thumb_path  = self.get_thumb_path(image)
            actual_path = self.get_actual_path(image)
            html += CamPage.templ_image_link.format(actual_image=actual_path,
                                                    alt_txt=image.d['ctime'],
                                                    thumb_image=thumb_path,
                                                    image_index=image.d['image_index'], # unique HTML ID for each image
                                                    max_num_images="{max_index}")  # replace later
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
            earlier_time = dtutils.sec_to_str(row.d['ctime_unix'],"%H:%M:%S")
            html += CamPage.templ_video_link.format(actual_video=video_fname,
                                                    earlier_time=earlier_time)

            n += 1
        #end
        return html

    def gen_row_html(self, html_images, html_videos, later_datetime, earlier_datetime,media_row_index):
        """
        given 
        html_images: html listing images
        html_videos: html listing videos
        later_datetime:  string specifying start datetime
        earlier_datetime: string specifying stop datetime

        return HTML for a single row
        """
        html = CamPage.templ_media_row.format(later_datetime = later_datetime,
                                              earlier_datetime = earlier_datetime,
                                              html_images = html_images,
                                              html_videos = html_videos,
                                              index=media_row_index)
        return html

    def make_status_dict(self, dest_fname, later_time_sec, earlier_time_sec):
        """
        make dictionary entry with generated HTML files and associated times
        """
        d={}
        assert later_time_sec >= earlier_time_sec, "assert later %d > earlier %d failed" % (later_time_sec,earlier_time_sec)
        d['page_fname'] = dest_fname
        d['later_time_sec'] = later_time_sec
        d['earlier_time_sec'] = earlier_time_sec
        return d

    def make_html_navbar(self, prev_fname, next_fname):
        html = CamPage.templ_navbar_html.format(cam_name=self.camera_name,
                                                url_next_page = next_fname,
                                                url_prev_page = prev_fname)
        return html
    
    
    def make_html_doc(self, carousel_html, media_html, navbar_html):
        if self.make_carousel==True:
            carousel_body_html = CamPage.templ_carousel_body_html.format(carousel_images_html = carousel_html,
                                                                         cam_name = self.camera_name)
        else:
            carousel_body_html = ''
        #end
        
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

        #
        # dont generate carousel if disabled
        if (self.make_carousel==False) or (len(image_list)==0):
            return ''
        #end

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
    
    def make_html_media_row(self, image_list, video_list, later_time_sec, earlier_time_sec, image_start_index):
        """
        return HTML for a single media row (images + video)
        """
        later_timefmt = "%a %b %d %H:%M:%S"
        earlier_timefmt = "%H:%M:%S"

        
        images_html  = self.make_html_image_list(image_list, image_start_index)
        videos_html  = self.make_html_video_list(video_list)
        later_datetime = dtutils.sec_to_str(later_time_sec, earlier_timefmt)
        earlier_datetime = dtutils.sec_to_str(earlier_time_sec, later_timefmt)
        row_html = CamPage.templ_media_row.format(later_datetime = later_datetime,
                                                  earlier_datetime = earlier_datetime,
                                                  html_images = images_html,
                                                  html_videos = videos_html)

        return row_html

    def make_html_media_row_blank(self):
        """
        return HTML for a single media row (images + video)
        """
        row_html = " <p>  &or; </p>"

        return row_html
    
    def generate(self, later_datetime, max_age_days, interval_min):
        """
        given
        later_datetime: starting datetime string (can specify "now")
        max_age_days: maximum number of days to include in webpage
        interval_min: time interval for each row in webpage

        generates 1 or more camera status webpages

        RETURNS
        status_page_list:  list of dictionary elements
        each dict has keys:
        'page_fname' : NOT preceded with www_dir, e.g. camera0_000.html and NOT www/camera0_000.html
        'later_time_sec'
        'earlier_time_sec'

        """
        status_page_list = []
        #
        # convert and compute datetime intervals in seconds
        later_time_sec = self.db.iso8601_to_sec(later_datetime)
        assert later_time_sec > 0

        final_earlier_time_sec = later_time_sec - int(max_age_days * 24.0 * 60.0 * 60.0) # days * (hrs/day)(min/hrs)(sec/min)
        assert (final_earlier_time_sec > 0)

        assert interval_min > 0
        interval_sec = int(interval_min * 60.0)

        # start a new web page
        media_row_index = 0
        carousel_html = ''
        media_html = ''

        # iterate through all rows which fall into the time interval
        # iterate backwards through time, from latest (later time) to oldest (earlier time)
        num_images_on_page = 0
        curr_file_later_time_sec = -1
        while(later_time_sec > final_earlier_time_sec):
            earlier_time_sec = later_time_sec - interval_sec
            row_image_list = self.db.select_by_time_cam_media(self.camera_name,
                                                         later_time_sec,
                                                         earlier_time_sec,
                                                         mediatype=datastore.MEDIA_IMAGE)
            row_video_list = self.db.select_by_time_cam_media(self.camera_name,
                                                         later_time_sec,
                                                         earlier_time_sec,
                                                         mediatype=datastore.MEDIA_VIDEO)
            #
            # if later_time0 not yet recorded, then do so
            if curr_file_later_time_sec <= 0:
                curr_file_later_time_sec = later_time_sec
            #end
            if (len(row_image_list)>0) or (len(row_video_list)>0):

                carousel_html += self.make_html_carousel(row_image_list, media_row_index)
                    
                media_html += self.make_html_media_row(row_image_list,
                                                       row_video_list,
                                                       later_time_sec,
                                                       earlier_time_sec,
                                                       num_images_on_page)
                media_row_index += 1
                num_images_on_page += len(row_image_list)
                
            else:
                #
                # insert a blank row to indicate passage of time
                media_html += self.make_html_media_row_blank()
            #end
            later_time_sec = earlier_time_sec
            
            if num_images_on_page >= self.max_images_per_page:
                #
                # close current webpage
                media_html = media_html.format(max_index=num_images_on_page)  # replace last template token
                dest_fname = self.write_webpage(carousel_html, media_html, False)
                status_page_list.append(self.make_status_dict(dest_fname, curr_file_later_time_sec, earlier_time_sec))
                
                #
                # start a new webpage
                media_row_index=0
                carousel_html = ''
                media_html = ''
                num_images_on_page = 0

                # reset later_time
                curr_file_later_time_sec = -1
            #end 
        #end
        
        # close last webpage (only if it has >= 1 image)
        if num_images_on_page > 0:
            media_html = media_html.format(max_index=num_images_on_page) # replace last template token
            dest_fname = self.write_webpage(carousel_html, media_html, True)
            status_page_list.append(self.make_status_dict(dest_fname, curr_file_later_time_sec, earlier_time_sec))
        #end

        #
        # for next time around, restart the suffix index
        self.fname_index=0
        
        return status_page_list

