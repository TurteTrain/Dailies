import "./entrypage.css"
//import Alex_Pic from '../assets/alex_pic.jpg'
//import Bernie_Pic from '../assets/bernie_pic.jpg'
//import Chris_Pic from '../assets/chris_pic.jpg'
import placeholder from "../assets/placeholder.jpg"

const Entrypage = ({ onSignIn }) => {



    return (
        <div className = "ep-container">
            <div className = "ep-actions">
                <button className = "ep-button" onClick={onSignIn}>
                    To Sign In
                </button>
                <button className = "ep-button" onClick = {() => window.open(
                    'https://github.com/TurteTrain/Dailies',
                    '_blank',
                    'noopener,noreferrer'
                )}>
                    To GitHub
                </button>
            </div>
            <div className = "ep-sections">
                <h2>Dailies</h2>
                <div className = "ep-container2">
                    <h2>The aim of Dailies is to give you the yearly "Spotify Wrapped" experience every day!</h2>
                    <h2> </h2>
                    <h2>See your days mood, top artists, or top songs!</h2>
                    <h2>Easy and safe to connect to Spotify!</h2>
                    <h2>Friend others to see their daily wrapped!</h2>
                    <h2>Easy to create an account!</h2>
                    <h2>Easy to delete your account!</h2>
                    <h1>SIGN UP NOW!</h1>
                </div>
                <h2>Our Team</h2>
                <div className = "ep-container2">
                    <h2>We are the ABCs!</h2>
                    <h2>----- A: Alexander Tuero ----- B: Bernardo Lopez ----- C: Cristian Ravelo -----</h2>
                    <div className = "row">
                        <img src={placeholder} alt="" />
                        <img src={placeholder} alt="" />
                        <img src={placeholder} alt="" />
                    </div>
                </div>
            </div>
        </div>
    );
}


export default Entrypage;