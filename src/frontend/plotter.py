import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import cartopy.crs as ccrs
import cartopy.feature as cfeature
import numpy as np
import pandas as pd
from shapely.geometry import Point
from shapely.affinity import scale
from shapely.ops import unary_union
from shapely.geometry import MultiPolygon
from scipy.stats import gaussian_kde
from matplotlib.collections import LineCollection

QUANTITY_NAMES = {
'lat': 'Latitude (deg)',
'lon': 'Longitude (deg)',
'baroaltitude': 'Barometric Altitude (m)',
'geoaltitude': 'Geometric Altitude (m)',
'heading': 'Heading (deg)',
'velocity': 'Velocity (m/s)'}
QUANTITY_NAMES_NO_UNITS = {
'lat': 'Latitude',
'lon': 'Longitude',
'baroaltitude': 'Barometric Altitude',
'geoaltitude': 'Geometric Altitude',
'heading': 'Heading',
'velocity': 'Velocity'}
class Plotter:
    """
    A class for creating plots of flight data.

    Attributes:
    - options: a dictionary containing configuration options for plotting.

    Methods:
    - __init__(self, config): Initializes a Plotter object.
    - set_quantity_ax_style(self, ax, title, quantity, legend=True): Sets the style of a plot of a single quantity.
    - set_route_ax_style(self, ax, title, legend=True): Sets the style of a plot of a flight route.
    - plot_quantity(self, state_vector_file, compressor, quantity, filename=None, ax=None, title=None): Plots a single quantity for a single flight.
    - plot_quantity_multi(self, state_vectors_files, compressor, quantity, filename=None, ax=None, title=None): Plots a single quantity for multiple flights.
    """
class Plotter:
    """
    Initializes a Plotter object.

    Args:
    - config: a dictionary containing configuration options for plotting.
    """
    def __init__(self, config):
        """
        Initializes a Plotter object.

        Args:
        - config: a dictionary containing configuration options for plotting.
        """
        self.options = config['plotting']

    def set_quantity_ax_style(self, ax, title, quantity, legend=True):
        """
        Sets the style of the given axis object with the specified title and quantity.

        Args:
            ax (matplotlib.axes.Axes): The axis object to set the style for.
            title (str): The title of the plot.
            quantity (int): The quantity to set the y-axis label for.
            legend (bool, optional): Whether to show the legend. Defaults to True.
        """
        ax.set_xlabel('Time (s)', fontsize=self.options['axis-fontsize'])
        ax.set_ylabel(QUANTITY_NAMES[quantity], fontsize=self.options['axis-fontsize'])
        ax.set_title(title, fontsize=self.options['title-fontsize'])
        if legend:
            ax.legend(fontsize=self.options['legend-fontsize'])
        ax.grid(True)
        
    def set_route_ax_style(self, ax, title, legend=True):
        """
        Sets the style of the given axis object for a flight route plot.

        Parameters:
        ax (cartopy.mpl.geoaxes.GeoAxesSubplot): The axis object to be styled.
        title (str): The title of the plot.
        legend (bool): Whether to show the legend or not. Default is True.

        Returns:
        None
        """
        if self.options['map-extent'] is None:
            # Set the extent of the plot based on the range of the plotted points
            x_min, x_max, y_min, y_max = ax.get_extent()
            RANGE = np.max([y_max - y_min, x_max - x_min])
            y_mid = (y_max + y_min)/2
            x_mid = (x_max + x_min)/2
            ax.set_extent([x_mid - RANGE/2, x_mid + RANGE/2, y_mid - RANGE/2, y_mid + RANGE/2])
        else:
            ax.set_extent(self.options['map-extent'])

        if legend:
            ax.legend(fontsize=self.options['legend-fontsize'])

        # ax.gridlines(draw_labels=True, fontsize=self.options['tick-fontsize'])
        gridlines = ax.gridlines(draw_labels=True)
        gridlines.xlabel_style = {'size': self.options['tick-fontsize'], 'color': 'gray'}
        gridlines.ylabel_style = {'size': self.options['tick-fontsize'], 'color': 'gray'}
        
        ax.set_title(title, fontsize=self.options['title-fontsize'])

        # For the 'Longitude' label at the bottom
        ax.text(0.5, -0.08, 'Longitude (deg)', va='bottom', ha='center',
                rotation='horizontal', rotation_mode='anchor',
                transform=ax.transAxes, fontsize=self.options['axis-fontsize'])

        # For the 'Latitude' label at the left
        ax.text(-0.12, 0.6, 'Latitude (deg)', va='center', ha='right',
                rotation='vertical', rotation_mode='anchor',
                transform=ax.transAxes, fontsize=self.options['axis-fontsize'])

    def plot_quantity(self, state_vector_file, compressor, quantity, filename=None, ax=None, title=None):
        """
        Plots a quantity over time from a state vector file using a given compressor.

        Args:
            state_vector_file (str): Path to the state vector file.
            compressor (Compressor): Compressor object used to decode the state vector file.
            quantity (str): Name of the quantity to plot.
            filename (str, optional): Path to save the figure as an image file. Defaults to None.
            ax (matplotlib.axes.Axes, optional): Axes object to plot on. Defaults to None.
            title (str, optional): Title of the plot. Defaults to None.

        Raises:
            ValueError: If both ax and filename are specified.

        Returns:
            matplotlib.figure.Figure: The figure object if filename is None, None otherwise.
        """        
        colormap = getattr(plt.cm, self.options['cmap'])

        if ax is not None and filename is not None:
            raise ValueError("Cannot specify both ax and filename")
        
        if ax is None:
            fig, ax = plt.subplots(figsize=self.options['fig-size'])
        else:
            fig = None
        df = compressor.decode_to_dataframe_from_file(state_vector_file)[['time', quantity]]
        if quantity not in df.columns:
            raise ValueError(f"Quantity {quantity} not found in state vector file.")
        df_interp = {col:[] for col in ['time', quantity]}
        df_interp = {'time':np.linspace(df['time'].iloc[0], df['time'].iloc[-1], num=self.options['point-precision'])}
        df_interp[quantity] = np.interp(df_interp['time'], df['time'], df[quantity])
        if quantity in ('lon', 'heading'):
            df_interp[quantity] = np.mod(df_interp[quantity], 360)
        xs, ys = pd.DataFrame(df_interp)[['time', quantity]].values.T

        ax.plot(xs, ys, color = colormap(1.))
        if title is None:
            self.set_quantity_ax_style(ax, f'Flight\'s {QUANTITY_NAMES_NO_UNITS[quantity]}', quantity, legend=False)
        else:
            self.set_quantity_ax_style(ax, title, quantity, legend=False)

        if fig is not None:
            fig.tight_layout()
        if filename is not None:
            fig.savefig(filename)

    def plot_quantity_multi(self, state_vectors_files, compressor, quantity, filename=None, ax=None, title=None):
        """
        Plots a quantity against time for multiple flights.

        Args:
            state_vectors_files (list of str): List of paths to state vector files.
            compressor (StateVectorsCompressor): Object used to decode the state vector files.
            quantity (str): Name of the quantity to plot.
            filename (str, optional): Path to save the figure. If None, the figure is not saved. Defaults to None.
            ax (matplotlib.axes.Axes, optional): Axes object to plot on. If None, a new figure is created. Defaults to None.
            title (str, optional): Title of the plot. If None, a default title is used. Defaults to None.

        Raises:
            ValueError: If both `ax` and `filename` are specified.
            ValueError: If the `quantity` is not found in the state vector files.

        Returns:
            matplotlib.figure.Figure: The figure object.
            matplotlib.axes.Axes: The axes object.
        """
        colormap = getattr(plt.cm, self.options['cmap'])

        if ax is not None and filename is not None:
            raise ValueError("Cannot specify both ax and filename")
        
        if ax is None:
            fig, ax = plt.subplots(figsize=self.options['fig-size'])
        else:
            fig = None
        
        ys = np.zeros((len(state_vectors_files), self.options['point-precision']))
        total_ts = np.zeros(len(state_vectors_files))
        for i, file in enumerate(state_vectors_files):
            df = compressor.decode_to_dataframe_from_file(file)[['time', quantity]]
            if quantity not in df.columns:
                raise ValueError(f"Quantity {quantity} not found in state vector file.")
            df_interp = {col:[] for col in ['time', quantity]}
            df_interp = {'time':np.linspace(df['time'].iloc[0], df['time'].iloc[-1], num=self.options['point-precision'])}
            df_interp[quantity] = np.interp(df_interp['time'], df['time'], df[quantity])
            if quantity in ('lon', 'heading'):
                df_interp[quantity] = np.mod(df_interp[quantity], 360)
            ys[i] = df_interp[quantity]
            total_ts[i] = df_interp['time'][-1] - df_interp['time'][0]
        
        mask = ~np.any(np.isnan(ys), axis=0)
        ys = ys[:, mask]
        xs = np.linspace(0, np.mean(total_ts), num=self.options['point-precision'])
        xs = np.tile(xs, (ys.shape[0],1))

        data = np.vstack([xs.ravel(), ys.ravel()])
        kde = gaussian_kde(data)
        kde_values = kde(data)
        kde_max = np.max(kde_values)
        kde_min = np.min(kde_values)
        colors_value = (kde_values - kde_min) / (kde_max - kde_min)
        colors_value = colors_value.reshape(ys.shape)

        segments = []
        colors = []
        # colors_value = np.array([(kde(ys[i,:]) - kde_min)/(kde_max - kde_min) for i in range(ys.shape[0])])

        for i in range(ys.shape[0]):
            for j in range(ys.shape[1]-1):
                segment = [(xs[i, j], ys[i,j]), (xs[i, j+1], ys[i,j+1])]
                segments.append(segment)
                colors.append(colormap(colors_value[i, j]))
        lc = LineCollection(segments, colors=colors, linewidth=2, alpha=1/np.sqrt(ys.shape[0]))

        ax.add_collection(lc)

        x_range = np.max(xs) - np.min(xs)
        y_range = np.max(ys) - np.min(ys)
        ax.set_xlim([np.min(xs) - x_range/10, np.max(xs) + x_range/10])
        ax.set_ylim([np.min(ys) - y_range/10, np.max(ys) + y_range/10])

        if title is None:
            self.set_quantity_ax_style(ax, f'Flights\' {QUANTITY_NAMES_NO_UNITS[quantity]}', quantity, legend=False)
        else:
            self.set_quantity_ax_style(ax, title, quantity, legend=False)
        
        if fig is not None:
            fig.tight_layout()
        if filename is not None:
            fig.savefig(filename)        

    def plot_quantity_shaded(self, state_vectors_files, compressor, quantity, filename=None, ax=None, title=None):
        """
        Plots a shaded area representing the deviation of a given quantity across multiple flights, along with the mean path.

        Args:
            state_vectors_files (list): A list of file paths containing state vectors for each flight.
            compressor (StateVectorsCompressor): An instance of StateVectorsCompressor used to decode the state vectors.
            quantity (str): The name of the quantity to plot.
            filename (str, optional): The file path to save the plot to. Defaults to None.
            ax (matplotlib.axes.Axes, optional): The axes to plot on. Defaults to None.
            title (str, optional): The title of the plot. Defaults to None.

        Raises:
            ValueError: If both ax and filename are specified.
            ValueError: If the given quantity is not found in the state vector file.
            ValueError: If the expectation measure or deviation measure is not recognized.

        Returns:
            None
        """    
        colormap = getattr(plt.cm, self.options['cmap'])

        if ax is not None and filename is not None:
            raise ValueError("Cannot specify both ax and filename")
        
        if ax is None:
            fig, ax = plt.subplots(figsize=self.options['fig-size'])
        else:
            fig = None
        
        ys = np.zeros((len(state_vectors_files), self.options['point-precision']))
        total_ts = np.zeros(len(state_vectors_files))
        for i, file in enumerate(state_vectors_files):
            df = compressor.decode_to_dataframe_from_file(file)[['time', quantity]]
            if quantity not in df.columns:
                raise ValueError(f"Quantity {quantity} not found in state vector file.")
            df_interp = {col:[] for col in ['time', quantity]}
            df_interp = {'time':np.linspace(df['time'].iloc[0], df['time'].iloc[-1], num=self.options['point-precision'])}
            df_interp[quantity] = np.interp(df_interp['time'], df['time'], df[quantity])
            if quantity in ('lon', 'heading'):
                df_interp[quantity] = np.mod(df_interp[quantity], 360)
            ys[i] = df_interp[quantity]
            total_ts[i] = df_interp['time'][-1] - df_interp['time'][0]
        
        mask = ~np.any(np.isnan(ys), axis=0)
        ys = ys[:, mask]

        if self.options['expectation-measure'] == 'mean':
            expectation_name = 'Mean Path'
            expectation = np.mean(ys, axis=0)
            t_final = np.mean(total_ts)
        elif self.options['expectation-measure'] == 'median':
            expectation_name = 'Median Path'
            expectation = np.median(ys, axis=0)
            t_final = np.median(total_ts)
        elif self.options['expectation-measure'] == 'average':
            expectation_name = 'Average Path'
            expectation = np.average(ys, axis=0)
            t_final = np.average(total_ts)
        else:
            raise ValueError(f"Expectation Measure not recognized: {self.options['expectation-measure']}")

        sigmas = sorted(self.options['deviation-values'])[::-1]
        if self.options['deviation-measure'] == 'std':
            sigma_names = [rf"${sigma:.1f}\sigma$ interval" for sigma in sigmas]
            sigma = [sig*np.std(ys, axis = 0) for sig in sigmas]
        elif self.options['deviation-measure'] == 'pct':
            sigma_names = [rf"${sigma:.1f}\%$ interval" for sigma in sigmas]
            sigma = [(np.percentile(ys, 50 + sig/2, axis = 0) - np.percentile(ys, 50 - sig/2, axis = 0))/2 for sig in sigmas]
        else:
            raise ValueError(f"Deviation Measure not recognized: {self.options['deviation-measure']}")
        
        ts = np.linspace(0, t_final, num=self.options['point-precision'])
        for i, _ in enumerate(sigmas):
            ax.fill_between(ts, expectation - sigma[i], expectation + sigma[i], alpha=0.5, color=colormap(float(i/len(sigmas))), label=sigma_names[i])
        
        ax.plot(ts, expectation, color = colormap(1.), label=expectation_name)

        y_range = np.max(ys) - np.min(ys)
        ax.set_ylim([np.min(ys) - y_range/10, np.max(ys) + y_range/10])

        if title is None:
            self.set_quantity_ax_style(ax, f'Distribution of Flights\' {QUANTITY_NAMES_NO_UNITS[quantity]}', quantity, legend=True)
        else:
            self.set_quantity_ax_style(ax, title, quantity, legend=True)
        
        if fig is not None:
            fig.tight_layout()
        if filename is not None:
            fig.savefig(filename)  

    def plot_route(self, state_vector_file, compressor, filename = None, ax = None, title = None):
        """
        Plots the route of a single aircraft based on its state vectors.

        Args:
        - state_vector_file: the file path containing state vectors for the aricraft.
        - compressor: a compressor object used to decode the state vectors.
        - filename(optional): the name of the file to save the plot to.
        - ax(optional): the axes to plot the data on.
        - title (optional): the title of the plot.
        """
        # Get the colormap to use for the plot
        colormap =  getattr(plt.cm, self.options['cmap'])

        if ax is not None and filename is not None:
            raise ValueError("Cannot specify both ax and filename")
        
        if ax is None:
            fig, ax = plt.subplots(subplot_kw={'projection': ccrs.PlateCarree()},
                               figsize=[self.options['fig-size'][0], self.options['fig-size'][0]])
        else:
            fig = None
        # Add features to the plot
        ax.add_feature(cfeature.BORDERS, linestyle=':')
        ax.add_feature(cfeature.COASTLINE)
        ax.add_feature(cfeature.STATES, linestyle=':')

        ys = np.zeros((2, self.options['point-precision']))
        df = compressor.decode_to_dataframe_from_file(state_vector_file)
        columns = ['lat', 'lon']
        df_interp = {col:[] for col in columns}
        df_interp = {'time':np.linspace(df['time'].iloc[0], df['time'].iloc[-1], num=self.options['point-precision'])}
        for col in columns:
            df_interp[col] = np.interp(df_interp['time'], df['time'], df[col])

        ys[0, :] = df_interp['lon']
        ys[1, :] = df_interp['lat']

        ax.plot(ys[0,:], ys[1,:], color = colormap(1.))
        if title is None:
            self.set_route_ax_style(ax, 'Aircraft Route', legend=False)
        else:
            self.set_route_ax_style(ax, title, legend=False)

        if fig is not None:
            fig.tight_layout()
        # Save the plot to a file
        if filename is not None:
            fig.savefig(filename)

    def plot_multiple_routes(self, state_vectors_files, compressor, filename = None, ax = None, title = None):
        """
        Plots the routes of multiple aircrafts based on their state vectors.

        Args:
        - state_vectors_files: a list of file paths containing state vectors for each aircraft.
        - compressor: a compressor object used to decode the state vectors.
        - filename(optional): the name of the file to save the plot to.
        - ax(optional): the axes to plot the data on.
        - title (optional): the title of the plot.
        """
        # Get the colormap to use for the plot
        colormap = getattr(plt.cm, self.options['cmap'])

        if ax is not None and filename is not None:
            raise ValueError("Cannot specify both ax and filename")
        
        if ax is None:
            fig, ax = plt.subplots(subplot_kw={'projection': ccrs.PlateCarree()},
                               figsize=[self.options['fig-size'][0], self.options['fig-size'][0]])
        else:
            fig = None

        try:
            # Add features to the plot
            ax.add_feature(cfeature.BORDERS, linestyle=':')
            ax.add_feature(cfeature.COASTLINE)
            ax.add_feature(cfeature.STATES, linestyle=':')
        except:
            raise ValueError("Invalid axes provided, did you remember to add \'subplot_kw={'projection': ccrs.PlateCarree()}\' to your axis?")
        ys = np.zeros((len(state_vectors_files), 2, self.options['point-precision']))
        # Loop through each state vectors file and plot the route
        for n, file in enumerate(state_vectors_files):
            # Decode the state vectors from the file and interpolate to get a fixed number of points
            df = compressor.decode_to_dataframe_from_file(file)
            columns = ['lat', 'lon']
            df_interp = {col:[] for col in columns}
            df_interp = {'time':np.linspace(df['time'].iloc[0], df['time'].iloc[-1], num=self.options['point-precision'])}
            for col in columns:
                df_interp[col] = np.interp(df_interp['time'], df['time'], df[col])

            ys[n, 0, :] = df_interp['lon']
            ys[n, 1, :] = df_interp['lat']
        mask = ~np.any(np.isnan(ys), axis=(1, 2))
        ys = ys[mask]

        if self.options['expectation-measure'] == 'mean':
            expectation_name = 'Mean Path'
            expectation = np.mean(ys, axis=0)
        elif self.options['expectation-measure'] == 'median':
            expectation_name = 'Median Path'
            expectation = np.median(ys, axis=0)
        elif self.options['expectation-measure'] == 'average':
            expectation_name = 'Average Path'
            expectation = np.average(ys, axis=0)
        else:
            raise ValueError(f"Expectation Measure not recognized: {self.options['expectation-measure']}")
        kde = gaussian_kde([np.ravel(ys[:,0,:]), np.ravel(ys[:,1,:])])
        kde_max = np.max(kde([np.ravel(ys[:,0,:]), np.ravel(ys[:,1,:])]))
        kde_min = np.min(kde([np.ravel(ys[:,0,:]), np.ravel(ys[:,1,:])]))
        segments = []
        colors = []

        colors_value = np.array([(kde([ys[i,0,:], ys[i,1,:]]) - kde_min)/(kde_max - kde_min) for i in range(ys.shape[0])])
        for i in range(ys.shape[0]):
            for j in range(ys.shape[2]-1):
                segment = [(ys[i,0,j], ys[i,1,j]), (ys[i,0,j+1], ys[i,1,j+1])]
                segments.append(segment)
                colors.append(colormap(colors_value[i, j]))
        lc = LineCollection(segments, colors=colors, linewidth=2, alpha=1/np.sqrt(ys.shape[0]))
        ax.add_collection(lc)
        
        if title is None:
            self.set_route_ax_style(ax, 'Aircraft Routes', legend=False)
        else:
            self.set_route_ax_style(ax, title, legend=False)
        

        if fig is not None:
            fig.tight_layout()
            # Save the plot to a file
            if filename is not None:
                fig.savefig(filename)

    def generate_confidence_region(self, means_x, means_y, sigma_x, sigma_y):
        """
        Generates a confidence region based on the means and standard deviations of x and y.

        Args:
            means_x (numpy.ndarray): Array of means for x.
            means_y (numpy.ndarray): Array of means for y.
            sigma_x (numpy.ndarray): Array of standard deviations for x.
            sigma_y (numpy.ndarray): Array of standard deviations for y.

        Returns:
            A shapely.geometry.polygon.Polygon object representing the confidence region.
        """
        ellipses = []
        for i in range(means_x.shape[0]):
            circle = Point(means_x[i], means_y[i]).buffer(1)
            ellipse = scale(circle, xfact=sigma_x[i], yfact=sigma_y[i], origin=(means_x[i], means_y[i]))
            ellipses.append(ellipse)
        union_ellipse = unary_union(ellipses)
        return union_ellipse

    def plot_multiple_routes_shaded(self, state_vectors_files, compressor, filename = None, ax = None, title = None):
        """
        Plots the routes of aircrafts with shaded regions representing deviations.
        
        Args:
        - state_vectors_files: a list of file paths containing state vectors for each aircraft.
        - compressor: a compressor object used to decode the state vectors.
        - filename (optional): the name of the file to save the plot to.
        - ax (optional): the axes to plot the data on.
        - title (optional): the title of the plot.
        """
        # Get the colormap to use for the plot
        colormap = getattr(plt.cm, self.options['cmap'])
        if ax is None:
            # Define the figure and axes for the plot
            fig, ax = plt.subplots(subplot_kw={'projection': ccrs.PlateCarree()},
                                figsize=[self.options['fig-size'][0], self.options['fig-size'][0]])
        else:
            fig = None
        # Add features to the plot
        ax.add_feature(cfeature.BORDERS, linestyle=':')
        ax.add_feature(cfeature.COASTLINE)
        ax.add_feature(cfeature.STATES, linestyle=':')

        ys = np.zeros((len(state_vectors_files), 2, self.options['point-precision']))
        # Loop through each state vectors file and plot the route
        for n, file in enumerate(state_vectors_files):
            # Decode the state vectors from the file and interpolate to get a fixed number of points
            df = compressor.decode_to_dataframe_from_file(file)
            columns = ['lat', 'lon']
            df_interp = {col:[] for col in columns}
            df_interp = {'time':np.linspace(df['time'].iloc[0], df['time'].iloc[-1], num=self.options['point-precision'])}
            for col in columns:
                df_interp[col] = np.interp(df_interp['time'], df['time'], df[col])

            ys[n, 0, :] = df_interp['lon']
            ys[n, 1, :] = df_interp['lat']

        mask = ~np.any(np.isnan(ys), axis=(1, 2))
        ys = ys[mask]

        if self.options['expectation-measure'] == 'mean':
            expectation_name = 'Mean Path'
            expectation = np.mean(ys, axis=0)
        elif self.options['expectation-measure'] == 'median':
            expectation_name = 'Median Path'
            expectation = np.median(ys, axis=0)
        elif self.options['expectation-measure'] == 'average':
            expectation_name = 'Average Path'
            expectation = np.average(ys, axis=0)
        else:
            raise ValueError(f"Expectation Measure not recognized: {self.options['expectation-measure']}")

        sigmas = sorted(self.options['deviation-values'])[::-1]
        exp_lon, exp_lat = expectation
        if self.options['deviation-measure'] == 'std':
            sigma_names = [rf"${sigma:.1f}\sigma$ interval" for sigma in sigmas]
            sigma_lon = [sig*np.std(ys[:,0,:], axis = 0) for sig in sigmas]
            sigma_lat = [sig*np.std(ys[:,1,:], axis = 0) for sig in sigmas]
        elif self.options['deviation-measure'] == 'pct':
            sigma_names = [rf"${sigma:.1f}\%$ interval" for sigma in sigmas]
            sigma_lon = [(np.percentile(ys[:,0,:], 50 + sig/2, axis = 0) - np.percentile(ys[:,0,:], 50 - sig/2, axis = 0))/2 for sig in sigmas]
            sigma_lat = [(np.percentile(ys[:,1,:], 50 + sig/2, axis = 0) - np.percentile(ys[:,1,:], 50 - sig/2, axis = 0))/2 for sig in sigmas]
        else:
            raise ValueError(f"Deviation Measure not recognized: {self.options['deviation-measure']}")
        
        regions = [self.generate_confidence_region(exp_lon, exp_lat, sigma_lon[i], sigma_lat[i]) for i in range(len(sigmas))]
        
        # Plot the interpolated points
        for i, _ in enumerate(sigmas):
            color = np.array(colormap(float(i/len(sigmas))))
            if isinstance(regions[i], MultiPolygon):
                label = sigma_names[i]
                for poly in regions[i].geoms:
                    x, y = poly.exterior.xy
                    ax.fill(x, y, color=color, alpha=0.5, label=label)
                    label=None
            else:
                x, y = regions[i].exterior.xy
                ax.fill(x, y, color=color, alpha=0.5, label=sigma_names[i])
        ax.plot(expectation[0], expectation[1], color = colormap(1.), linewidth = 2, label = expectation_name)

        if title is None:
            self.set_route_ax_style(ax, 'Aircraft Route Distribution')
        else:
            self.set_route_ax_style(ax, title)
        
        if fig is not None:
            fig.tight_layout()
            # Save the plot to a file
            if filename is not None:
                fig.savefig(filename)
