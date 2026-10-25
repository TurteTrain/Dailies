import { useRef, useState, useEffect } from 'react';
import './login.css'
import { api } from '../api.js'

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
    const [busy, setBusy] = useState(false);

    //focus the username box when the page loads or the mode changes
    useEffect(() => {
        userRef.current?.focus();
    }, [action])
    //trying to capture the inputs (changing an input also clears the error message)
    function get_username(e){
        setUsername(e.target.value);
        setErrMsg('');
    }
    function get_email(e){
        setEmail(e.target.value);
        setErrMsg('');
    }
    function get_password(e){
        setPassword(e.target.value);
        setErrMsg('');
    }

    //sends the request to Django; on success Django has already created the session cookie
    async function send(path, body){
        setBusy(true);
        try {
            const user = await api(path, { method: 'POST', body });
            onSuccess(user);
        } catch (err) {
            setErrMsg(err.message);
        } finally {
            setBusy(false);
        }
    }

    //functions for button submission
    function check_sign_up(){
        if(action === "Sign Up"){
            if(!username.trim() || !password){
                setErrMsg("Username and password are required");
            }
            else if(!email.includes("@")){
                setErrMsg("Invalid Email");
            }
            else{
                send('register', { username: username.trim(), email: email.trim(), password });
            }
        }
        else {
            setAction("Sign Up");
        }
    }
    function check_login(){
        if(action === "Login"){
            if(!username.trim() || !password){
                setErrMsg("Username and password are required");
            }
            else{
                send('login', { username: username.trim(), password });
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
                <div className = "input">
                    <img src={user_icon} alt="" />
                    <input ref={userRef} type = "text" placeholder = "Username"
                                value = {username} onChange = {get_username}/>
                </div>
                {action==="Login"? <div></div>:
                    <div className = "input">
                        <img src={email_icon} alt="" />
                        <input type = "email" placeholder = "Email"
                                        value = {email} onChange = {get_email}/>
                    </div>
                }
                <div className = "input">
                    <img src={lock_icon} alt="" />
                    <input type = "password" placeholder = "Password"
                                    value = {password} onChange = {get_password}/>
                </div>
            </div>

            {/*THIS SECTION IS THE BUTTONS!!!!*/}
            <div className = "submit-container">
                <button disabled = {busy} className = {action==="Login"?"submit gray":"submit"} onClick = {check_sign_up}>Sign Up</button>
                <button disabled = {busy} className = {action==="Sign Up"?"submit gray":"submit"} onClick = {check_login}>Login</button>
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
