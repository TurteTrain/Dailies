import React, { useRef, useState, useEffect } from 'react';
import './login.css'

import lock_icon from '../assets/lock.png'
import email_icon from '../assets/mention.png'
import user_icon from '../assets/user.png'

const Login = ({ onSuccess }) => {

    const userRef = useRef(null);
    const errRef = useRef(null);

    const [action, setAction] = useState("Sign Up");

    const [username, setUsername] = useState('');
    const [email, setEmail] = useState('');
    const [password, setPassword] = useState('');
    const [errorMessage, setErrMsg] = useState('');
    const [success, setSuccess] = useState(false);

    //if the user changes input boxes it will clear error message
    useEffect(() => {
        userRef.current?.focus();
    }, [])
    useEffect(() => {
        setErrMsg('');
    }, [username, email, password])

    //trying to capture the inputs
    function get_username(e){
        setUsername(e.target.value);
    }
    function get_email(e){
        setEmail(e.target.value);
    }
    function get_password(e){
        setPassword(e.target.value);
    }

    //functions for button submission
    function check_sign_up(){
        if(action === "Sign Up"){
            if(true) {
                onSuccess({username, email})
            }
            //FUTURE CHECK FOR VALID EMAIL?
            else{
                setErrMsg("Invalid Email")
            }
        }
        else {
            setAction("Sign Up");
        }
    }
    function check_login(){
        if(action === "Login"){
            if(email === "email@gmail.com" && password === "password"){
                //accept, go to next page
                //fetch username from email?
                onSuccess({username: "insert username", email})
            }
            else{
                setErrMsg("Invalid Email or Password")
            }
        }
        else{
            setAction("Login")
        }
    }

    return (
        <div className = 'container'>
            <div className = "header">
                <div className = "text">{action}</div>
                <div className = "underline"></div>
            </div>

            {/*THIS SECTION IS TEXT INPUTS!!!!*/}
            <div className = "inputs">
                {action==="Login"? <div></div>:
                    <div className = "input">
                        <img src={user_icon} alt="" />
                        <input ref={userRef} type = "text" placeholder = "Username"
                                value = {username} onChange = {get_username}/>
                    </div>
                }
                <div className = "input">
                    <img src={email_icon} alt="" />
                    <input type = "email" placeholder = "Email"
                                    value = {email} onChange = {get_email}/>
                </div>
                <div className = "input">
                    <img src={lock_icon} alt="" />
                    <input type = "password" placeholder = "Password"
                                    value = {password} onChange = {get_password}/>
                </div>
            </div>

            {/*THIS SECTION IS THE BUTTONS!!!!*/}
            <div className = "submit-container">
                <button className = {action==="Login"?"submit gray":"submit"} onClick = {check_sign_up}>Sign Up</button>
                <button className = {action==="Sign Up"?"submit gray":"submit"} onClick = {check_login}>Login</button>
            </div>

            {/*THIS SECTION IS THE ERROR MESSAGE FOR INVALID INPUTS!!!!*/}
            <section>
                <p ref={errRef} className={errorMessage ? "errorMessage"
                    : "offscreen"} aria-live="assertive">{errorMessage}</p>
            </section>
        </div>
    );
};

export default Login;