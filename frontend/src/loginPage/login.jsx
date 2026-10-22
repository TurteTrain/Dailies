import React, { useState } from 'react';
import './login.css'

import lock_icon from '../assets/lock.png'
import email_icon from '../assets/mention.png'
import user_icon from '../assets/user.png'

const Login = () => {

    const [action, setAction] = useState("Sign Up");

    return (
        <div className = 'container'>
            <div className = "header">
                <div className = "text">{action}</div>
                <div className = "underline"></div>
            </div>
            <div className = "inputs">
                {action==="Login"? <div></div>:
                    <div className = "input">
                        <img src={user_icon} alt="" />
                        <input type = "text" placeholder = "Username"/>
                    </div>
                }
                <div className = "input">
                    <img src={email_icon} alt="" />
                    <input type = "email" placeholder = "Email"/>
                </div>
                <div className = "input">
                    <img src={lock_icon} alt="" />
                    <input type = "password" placeholder = "Password" />
                </div>
            </div>
            <div className = "submit-container">
                <div className = {action==="Login"?"submit gray":"submit"} onClick = {()=>{setAction("Sign Up")}}>Sign Up</div>
                <div className = {action==="Sign Up"?"submit gray":"submit"} onClick = {()=>{setAction("Login")}}>Login</div>
            </div>
            {action==="Sign Up"?<div></div>:
                <div className = "forgot-password">
                    <span>Forgot Password?</span>
                </div>
            }
        </div>
    );
};

export default Login;