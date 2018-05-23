
import datastore
import time
import os
"""

  
"""
class IndexPage:
    #
    # {camera_rows} = concatenated camera rows; see templ_camera_row
    templ_webpage = unicode("""
<!DOCTYPE html>
<html lang="en">
  <head>
    <meta charset="utf-8">
    <meta http-equiv="X-UA-Compatible" content="IE=edge">
    <meta name="viewport" content="width=device-width, initial-scale=1">

    <title>Bootstrap 4, from LayoutIt!</title>

    <meta name="description" content="panopticon">
    <meta name="author" content="Robert Yu, Buttersquid Inc">

    <link href="css/bootstrap.min.css" rel="stylesheet">
    <link href="css/style.css" rel="stylesheet">

  </head>
  <body>

    <div class="container-fluid">
	<div class="row">
		<div class="col-md-12">
			<h3>
				Panopticon
			</h3>
			<table class="table table-sm">
				<thead>
					<tr>
						<th>
							#
						</th>
						<th>
							Camera Name
						</th>
						<th>
							Description
						</th>
						<th>
							Status Page
						</th>
 				                <th>
						        Live Video
						</th>
					</tr>
				</thead>
{camera_rows}
			</table>
		</div>
	</div>
	<div class="row">
		<div class="col-md-12">
			<h2>
				Activity Summary
			</h2>
			<p>
			    Here's where we put a summary plot of activity vs time
			</p>
			<p>
			    <a class="btn" href="#">View details </a>
			</p>
		</div>
	</div>
    </div>

    <script src="js/jquery.min.js"></script>
    <script src="js/bootstrap.min.js"></script>
    <script src="js/scripts.js"></script>
  </body>
    """)
    #
    # templ_row placeholders:
    # {upper_datetime} = upper  date and time, e.g. 2018-03-22 10:10:00
    # {lower_datetime} = lower date and time
    # {html_images} = HTML of images
    # {html_videos} = HTML of videos
    templ_cam_row = unicode("""
				<tbody>
					<tr class="table-active">
						<td>
							{camera_index}
						</td>
						<td>
							{camera_name}
						</td>
						<td>
							{camera_descr}
						</td>
						<td>
							{webpage_url}
						</td>
						<td>
						        {live_link_url}
					        </td>
					</tr>
				</tbody>
    """)

    def __init__(self, dest_fname="index.html"):
        self.www_dir = os.path.join(os.getcwd(), "www")
        assert os.path.exists(self.www_dir)

        self.dest_fname = os.path.join(self.www_dir, dest_fname)
        self.dest_file = open(dest_fname, "wt")

    def make_index(self, cam_page_fname_list, cam_list):
        assert len(cam_page_fname_list)==len(cam_list)
        rows_html = ''
        for n in range(len(cam_list)):
            rows_html += IndexPage.templ_cam_row.format(camera_index=n,
                                                        camera_name=cam_list[n]['name'],
                                                        camera_descr=cam_list[n]['description'],
                                                        webpage_url=cam_page_fname_list[n],
                                                        live_link_url=cam_list[n]['live_url'])
                             
        f = open(self.dest_fname, "wt")
        f.write(IndexPage.templ_webpage.format(camera_rows = rows_html))
        f.close()

        return self.dest_fname

        
        
        
        
