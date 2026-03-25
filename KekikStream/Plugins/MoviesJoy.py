# Bu araç @keyiflerolsun tarafından | @KekikAkademi için yazılmıştır.

from KekikStream.Core.Plugin.FlwBasePlugin import FlwBasePlugin

class MoviesJoy(FlwBasePlugin):
    name        = "MoviesJoy"
    language    = "en"
    main_url    = "https://moviesjoy.is"
    favicon     = f"https://www.google.com/s2/favicons?domain={main_url}&sz=64"
    description = "Watch HD Movies online and Stream latest tv-series, Over 200000 videos to stream in HD with English and Spanish subtitle. Join MoviesJoy today to begin watching movies online."

    main_page   = {
        f"{main_url}/movie?page="             : "Movies",
        f"{main_url}/tv-show?page="           : "TV Shows",
        f"{main_url}/top-imdb?page="          : "Top IMDB",
        f"{main_url}/genre/action?page="      : "Action",
        f"{main_url}/genre/adventure?page="   : "Adventure",
        f"{main_url}/genre/animation?page="   : "Animation",
        f"{main_url}/genre/comedy?page="      : "Comedy",
        f"{main_url}/genre/crime?page="       : "Crime",
        f"{main_url}/genre/documentary?page=" : "Documentary",
        f"{main_url}/genre/drama?page="       : "Drama",
        f"{main_url}/genre/family?page="      : "Family",
        f"{main_url}/genre/fantasy?page="     : "Fantasy",
        f"{main_url}/genre/history?page="     : "History",
        f"{main_url}/genre/horror?page="      : "Horror",
        f"{main_url}/genre/romance?page="     : "Romance",
        f"{main_url}/genre/thriller?page="    : "Thriller",
    }
