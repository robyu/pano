
import datastore
import time
import os
"""

  
"""
class CamPage:
    #
    # {cam_name} = camera name
    templ_header = unicode("""
<!DOCTYPE html>
<html lang="en">
   <head>
      <meta charset="utf-8">
      <meta http-equiv="X-UA-Compatible" content="IE=edge">
      <meta name="viewport" content="width=device-width, initial-scale=1">

      <title>Panopticon:{cam_name}</title>

      <meta name="description" content="panopticon">
      <meta name="author" content="Robert Yu, Buttersquid Inc">

      <link href="css/bootstrap.min.css" rel="stylesheet">
      <link href="css/style.css" rel="stylesheet">

      <META HTTP-EQUIV="refresh" CONTENT="300"> 

      <FORM>
      <INPUT TYPE="button" onClock="history.go(0)" VALUE="Refresh">
      </FORM>

   </head>
   <div class="container-fluid">
    """)
    templ_footer=unicode("""
   </div>
   <script src="js/jquery.min.js"></script>
   <script src="js/bootstrap.min.js"></script>
   <script src="js/scripts.js"></script>
   </body>
</html>
    """)

    #
    # templ_row placeholders:
    # {upper_datetime} = upper  date and time, e.g. 2018-03-22 10:10:00
    # {lower_datetime} = lower date and time
    # {html_images} = HTML of images
    # {html_videos} = HTML of videos
    templ_row = unicode("""
	<div class="row">
	    <div class="col-md-6">
		<h2>
		    {upper_datetime}..{lower_datetime}
		</h2>
		<p>
                    {html_images}
		</p>
	    </div>
	    <div class="col-md-6">
		<h2>
		    Col 2
		</h2>
		<p>
                   <ul class="list-group">
                       {html_videos}
                   </ul>
		</p>
		<p>
		    <a class="btn" href="#">View details</a>
		</p>
	    </div>
	</div>
    """)

    templ_list_image=unicode("""
    <li class="list-group-item">
       {image_list}
    </li>
    """)

    #
    #<img alt="Bootstrap Image Preview" src="http://www.layoutit.com/img/sports-q-c-140-140-3.jpg">
    #

    def __init__(self, camera_name, db, derived_dir, base_dir, www_dir):
        self.db = db  # pointer to datastore
        self.derived_dir = derived_dir
        self.base_dir = base_dir
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
        self.temp_fname = os.path.join(self.www_dir, "tmp_camera.html")

        self.fname_index=0

    def calc_dest_fname(self):
        dest_fname = "%s-%04d.html" % (self.camera_name, self.fname_index)
        self.fname_index += 1
        return dest_fname
        
    def write_header(self, dest_file):
        """
        write html header to webpage
        """
        dest_file.write(CamPage.templ_header.format(cam_name=self.camera_name))
        return

    def write_footer_and_close(self, dest_file):
        """
        write html footer and close file 
        """
        dest_file.write(CamPage.templ_footer)
        dest_file.close()

    def move_temp_to_dest_fname(self, temp_fname, dest_fname):
        
        #
        # remove existing dest_fname, rename temp to dest_fname
        full_dest_fname = os.path.join(self.www_dir, dest_fname)
        if os.path.exists(full_dest_fname):
            os.remove(full_dest_fname)
        #end

        os.rename(temp_fname, full_dest_fname)


    def get_thumb_path(self, row):
        """
        return the abs path to the derived image/video file
        OR a default image (if the derived file does not exist)
        """
        if len(row.d['derived_fname']) == 0:   # no thumbnail
            thumb_path = self.default_image_fname
        else:
            thumb_path = os.path.join(self.derived_dir, row.d['derived_fname'])
        #end
        assert os.path.exists(thumb_path)
        return thumb_path

    def get_actual_path(self, row):
        """
        return the abs path to the actual image/video source file
        """
        actual_path = os.path.join(self.base_dir, row.d['path'], row.d['fname'])
        assert os.path.exists(actual_path)
        return actual_path
    
        
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
            html += "<p>\n"
            for m in range(self.num_images_per_row):
                row = image_row_list[n+m]
                thumb_path  = self.get_thumb_path(row)
                actual_path = self.get_actual_path(row)
                html += """<a href="{actual_image}"> <img alt="{alt_txt}" src="{thumb}"></a>\n"""\
                                    .format(actual_image=actual_path,
                                            alt_txt=row.d['ctime'],
                                            thumb=thumb_path)
            #end
            html += "</p>\n"
            n += self.num_images_per_row
        #end
        assert len(image_row_list) - n < self.num_images_per_row

        #
        # make a row of the remaining imagees
        html += "<p>\n"
        while n < len(image_row_list):
            row = image_row_list[n]
            thumb_path  = self.get_thumb_path(row)
            actual_path = self.get_actual_path(row)
            html += """<a href="{actual_image}"> <img alt="{alt_txt}" src="{thumb}"></a>\n"""\
                                .format(actual_image=actual_path,
                                        alt_txt=row.d['ctime'],
                                        thumb=thumb_path)
            n += 1
        #end
        html += "</p>\n"
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
            html += "<p>\n"
            video_fname = row.d['derived_fname']
            assert os.path.exists(video_fname)
            html += """<a href="{actual_video}">{label}</a>\n"""\
                                .format(actual_video=video_fname,
                                        label=row.d['ctime'])

            html += "</p>\n"
            n += 1
        #end
        return html

    def write_row(self, html_images, html_videos, upper_datetime, lower_datetime):
        """
        given 
        html_images: html listing images
        html_videos: html listing videos
        upper_datetime:  string specifying start datetime
        lower_datetime: string specifying stop datetime

        write a "row" to the webpage
        """
        html = CamPage.templ_row.format(upper_datetime = upper_datetime,
                                        lower_datetime = lower_datetime,
                                        html_images = html_images,
                                        html_videos = html_videos)
        self.dest_file.write(html)
        return
        
    def generate(self, upper_datetime, max_age_days, interval_min):
        """
        given
        upper_datetime: starting datetime string
        max_age_days: maximum number of days to include in webpage
        interval_min: time interval for each row in webpage

        generate a complete webpage

        RETURNS
        list of generated HTML webpages NOT preceded with www_dir,
        e.g.
        camera0_000.html
        NOT www/camera0_000.html
        """
        dest_fname_list = []
        #
        # convert and compute datetime intervals in seconds
        upper_time_sec = self.db.iso8601_to_sec(upper_datetime)
        assert upper_time_sec > 0

        final_lower_time_sec = upper_time_sec - int(max_age_days * 24.0 * 60.0 * 60.0) # days * (hrs/day)(min/hrs)(sec/min)
        assert (final_lower_time_sec > 0)

        assert interval_min > 0
        interval_sec = int(interval_min * 60.0)
        # generate webpage
        self.dest_file = open(self.temp_fname, "wt")
        
        self.write_header(self.dest_file)
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
                image_html = self.make_html_image_list(row_image_list)
                video_html = self.make_html_video_list(row_video_list)
                start_datetime = self.db.sec_to_iso8601(upper_time_sec)
                stop_datetime = self.db.sec_to_iso8601(lower_time_sec)
                self.write_row(image_html, video_html, start_datetime, stop_datetime)
            #end
            upper_time_sec = lower_time_sec
        #end
        
        self.write_footer_and_close(self.dest_file)

        dest_fname = self.calc_dest_fname()
        self.move_temp_to_dest_fname(self.temp_fname, dest_fname)

        dest_fname_list.append(dest_fname)

        #
        # for next time around, restart the suffix index
        self.fname_index=0
        
        return dest_fname_list
    
