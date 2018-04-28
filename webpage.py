
import datastore
import time
import os
"""

  
"""
class Webpage:
    dest_dir = 'html'

    #
    # {row} = HTML of row class
    templ_header = unicode("""
<!DOCTYPE html>
<html lang="en">
   <head>
      <meta charset="utf-8">
      <meta http-equiv="X-UA-Compatible" content="IE=edge">
      <meta name="viewport" content="width=device-width, initial-scale=1">

      <title>Panopticon</title>

      <meta name="description" content="panopticon">
      <meta name="author" content="Robert Yu, Buttersquid Inc">

      <link href="css/bootstrap.min.css" rel="stylesheet">
      <link href="css/style.css" rel="stylesheet">

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
    # {datetime_upper} = upper  date and time, e.g. 2018-03-22 10:10:00
    # {datetime_lower} = lower date and time
    # {html_images} = HTML of images
    # {html_videos} = HTML of videos
    templ_row = unicode("""
	<div class="row">
	    <div class="col-md-6">
		<h2>
		    {datetime_upper}..{datetime_lower}
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

    def __init__(self, dest_fname, base_dir='.', derived_dir='derived'):
        self.dest_fname = dest_fname
        self.dest_file = open(dest_fname, "wt")
        self.num_images_per_row = 4
        self.base_dir = os.path.abspath(base_dir)
        assert os.path.exists(self.base_dir)

        self.www_dir = os.path.join(os.getcwd(), 'www')
        assert os.path.exists(self.www_dir)

        self.default_image_fname = os.path.join(self.www_dir, 'mryuck.png')
        assert os.path.exists(self.default_image_fname)

        self.derived_dir = os.path.abspath(derived_dir)
        assert os.path.exists(self.derived_dir)
        
    def write_header(self):
        """
        write html header to webpage
        """
        self.dest_file.write(Webpage.templ_header)
        return

    def write_row(self,cam_name, start_time, delta_min, row_image_list, row_video_list):
        """
        write a row (corresponding to time interval)
        with image list and video list
        """
        return

    def close(self):
        """
        write html footer and close file 
        """
        self.dest_file.write(Webpage.templ_footer)
        self.dest_file.close()


    def get_thumb_path(self, row):
        """
        return the abs path to the derived image/video file
        OR a default image (if the derived file does not exist)
        """
        if len(row.d['derived_fname']) == 0:
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
        return HTML
        """
        html = ''
        n = 0
        
        while n+self.num_images_per_row < len(image_row_list):
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
        html = ''
        n = 0
        
        while n < len(video_row_list):
            row = video_row_list[n]
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

    def write_row(self, html_images, html_videos, datetime_upper, datetime_lower):
        html = Webpage.templ_row.format(datetime_upper = datetime_upper,
                                        datetime_lower = datetime_lower,
                                        html_images = html_images,
                                        html_videos = html_videos)
        self.dest_file.write(html)
        return
        
    
        
        
        
        
        
        
        
