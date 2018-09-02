
import datastore
import time
import os
import dtutils
"""

  
"""
class IndexPage:
    #
    # cam_summary_rows
    # cam_status_rows
    templ_webpage = unicode("""
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
  <body>

    <div class="container-fluid">
	<div class="row">
		<div class="col-md-12">
		    <h3>
			Panopticon
		    </h3>
                    <!--  SUMMARY TABLE HEADER -->
		    <table class="table table-sm">
			<thead>
			    <tr>
				<th>
				    Camera Name
				</th>
				<th>
				    Description
				</th>
 				<th>
				    Admin Login
				</th>
 				<th>
				    Live Video
				</th>
			    </tr>
			</thead>
                        <!- summary rows go here ->
                        {cam_summary_rows}
		    </table>
                    <!-- CAMERA STATUS HEADER -->
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
                                    Start 
                                </th>
                                <th>
                                    Stop
                                </th>
				<th>
				    Status Page
				</th>
			    </tr>
			</thead>
                        <!- camera status rows go here ->
                        {cam_status_rows}
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
    # {camera_name}
    # {camera_descr}
    # {admin_url}
    # {live_url}
    templ_summary_row = unicode("""
                        <!-- SUMMARY ROW -->                        
                        <tbody>
                            <tr class="table-active" >
                                <td>
                                    {camera_name}
                                </td>
                                <td>
                                    {camera_descr}
                                </td>
                                <td>
                                    <a href="{admin_url}">admin_url</a>
                                </td>
                                <td>
                                    <a href={live_url}>live-link</a>
                                </td>
                            </tr>
                        </tbody>
    """)
    #
    # templ_row placeholders:
    # {index}
    # {camera_name}
    # {lower_datetime} = lower date and time
    # {upper_datetime} = upper  date and time
    # {webpage_url} = status webpage URL
    templ_status_row = unicode("""
                        <!-- CAMERA STATUS ROW -->                        
                        <tbody>
                            <tr class="table-active" >
                                <td>
                                    {index}
                                </td>
                                <td>
                                    {camera_name}
                                </td>
                                <td>
                                    {lower_datetime}
                                </td>
                                <td>
                                    {upper_datetime}
                                </td>
                                <td>
                                    <a href="{webpage_url}">{webpage_url}</a>
                                </td>
                            </tr>
                        </tbody>
    """)

    def __init__(self, www_dir, dest_fname="index.html"):
        self.www_dir = www_dir
        assert os.path.exists(self.www_dir)

        self.dest_fname = dest_fname

    def generate_summary_rows(self, cam_list):
        """
        generate HTML for summary table rows
        """
        rows_html = ''
        for cam_info in cam_list:
            rows_html += IndexPage.templ_summary_row.format(camera_name = cam_info['name'],
                                                            camera_descr = cam_info['description'],
                                                            admin_url=cam_info['admin_url'],
                                                            live_url = cam_info['live_url'])
        #end
        return rows_html

    def generate_status_rows(self, cam_list):
        """
        generate HTML for status table rows
        """
        rows_html = ''
        index=0
        for cam_info in cam_list:
            for page_dict in cam_info['status_page_list']:
                #
                # each dict entry in status_page_list has these keys (see campage.py::generate)
                # lower_time_sec
                # upper_time_sec
                # page_fname
                page_fname = page_dict['page_fname']
                
                # STOPPED HERE
                # sec to iso8601?
                #lower_dt = str(page_dict['lower_time_sec']) #"Sun Aug 26 2018 14:00"
                fmt = "%a %b %d %H:%M:%S"
                lower_dt = dtutils.sec_to_str(page_dict['lower_time_sec'],fmt)
                upper_dt = dtutils.sec_to_str(page_dict['upper_time_sec'],fmt)
                rows_html += IndexPage.templ_status_row.format(index=index,
                                                               camera_name=cam_info['name'],
                                                               lower_datetime = lower_dt,
                                                               upper_datetime = upper_dt,
                                                               webpage_url=page_fname)
                index += 1
            #end
        #end
        return rows_html
        
        
    def make_index(self, cam_list):
        """
        IN:
        cam_list:  list of per-cam dictionary objects
        """
        summary_html = self.generate_summary_rows(cam_list)
        status_html = self.generate_status_rows(cam_list)

        full_dest_fname = os.path.join(self.www_dir, self.dest_fname)
        f = open(full_dest_fname, "wt")
        f.write(IndexPage.templ_webpage.format(cam_summary_rows = summary_html,
                                               cam_status_rows = status_html))
        f.close()

        return self.dest_fname
    
        
        
        
        
