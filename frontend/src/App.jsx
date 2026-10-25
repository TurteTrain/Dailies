import { useState } from 'react'

import Login from './loginPage/login.jsx'
import Homepage from './homepage/homepage.jsx'
import './App.css'

function App() {

    const [count, setCount] = useState(0);

    const [success, setSuccess] = useState(false);
    const[userDetails, setUserDetails] = useState({});

    function login_Success(userDetails){
        setSuccess(true);
        setUserDetails(userDetails);
    }

    return (
        <div>
            {/*If login successful then call login_success to set userdetails and then go to homepage*/}
            {success ? <Homepage userDetails = {userDetails}/> : <Login onSuccess={login_Success}/>}
        </div>
    )
}

export default App
