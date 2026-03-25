# Bu araç @keyiflerolsun tarafından | @KekikAkademi için yazılmıştır.

from KekikStream.Core.Plugin.FlwBasePlugin import FlwBasePlugin


class BFlix(FlwBasePlugin):
    name        = "BFlix"
    language    = "en"
    main_url    = "https://fmovies.llc"
    favicon     = f"https://www.google.com/s2/favicons?domain={main_url}&sz=64"
    description = "Watch free Streaming movies and TV shows online in HD quality. You can also Download movies for free here on Fmovies website"

    main_page   = {
        f"{main_url}/movie?page="          : "Movies",
        f"{main_url}/tv-show?page="        : "TV Shows",
        f"{main_url}/top-imdb?page="       : "Top IMDB",
        f"{main_url}/genre/action?page="   : "Action",
        f"{main_url}/genre/comedy?page="   : "Comedy",
        f"{main_url}/genre/drama?page="    : "Drama",
        f"{main_url}/genre/horror?page="   : "Horror",
        f"{main_url}/genre/romance?page="  : "Romance",
        f"{main_url}/genre/thriller?page=" : "Thriller",
    }
