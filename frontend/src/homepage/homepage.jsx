import './homepage.css'
import React from "react";

const Homepage = ({ userDetails }) => {

    return(
        <div>
            <div className = "header">
                <div className = "text">{userDetails.username}</div>
                <div className = "text">{userDetails.email}</div>
            </div>
        </div>
    );

}

export default Homepage;